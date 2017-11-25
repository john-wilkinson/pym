"""
The install module has the logic for installing the packages

1. Calculate the list of references
2. Calculate initial dependency graph
3. Download packages
    a. Download to staging area
    b. Re-calculate dependency graph
    c. Resolve any dependencies
4. Unstage dependencies in staging area
"""

import os
import re
import copy
import json
import stat
import errno
import shutil
import requests
import functools
import itertools
import collections
import wheel.install
from git import Repo, exc
from bs4 import BeautifulSoup

### DEBUG
import psutil

from . import pypi
from . import semver
from .commands import PymCommand
from .package import PymPackage, PymConfigBuilder, PackageInfo
from .exceptions import InstallerNotFoundException, VersionNotFoundException, PymPackageException, PackageUrlException


class InstallCommand(PymCommand):
    """
    1. Download package into staging area
    2. Create manifest for current package versions
    3. Determine dependencies of current packages
    4. Resolve dependencies by downloading more packages, etc
    """
    COMMAND = 'install'

    @classmethod
    def args(cls, subparsers):
        subparser = subparsers.add_parser(InstallCommand.COMMAND, help='Install the specified package(s)',
                                          epilog='Example: pym install --save https://github.com/tornadoweb/tornado.git')
        subparser.add_argument('packages', help='Package name (or git location)', nargs='*', metavar='package')
        subparser.add_argument('--save', help='Save the package to local config', action='store_true')

    @classmethod
    def make(cls, cli, args, path):
        project = PymPackage.load(path)
        installers = [
            GitInstaller,
            PypiInstaller
        ]
        return cls(cli, installers, project)

    def __init__(self, cli, installers, project):
        super(InstallCommand, self).__init__(cli)
        self.installers = installers
        self.project = project
        self.packages_key = 'dependencies'

    def cleanup(self):
        staging_dir = self.project['staging_location']
        dest = os.path.join(self.project.location, staging_dir)
        rmdir(dest)

    def run(self, args):
        install_list = args['packages']
        save = args['save']
        staging_dir = self.project['staging_location']
        install_dir = self.project['install_location']

        if install_list:
            references = set(install_list)
            installables = [self.find_ref_installer(reference) for reference in references]
        else:
            references = self.project[self.packages_key].items()
            installables = [self.find_installer(name, version) for name, version in references]

        dest = os.path.join(self.project.location, staging_dir)

        try:
            os.makedirs(dest)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        packages = []

        for installer, info in installables:
            packages.append(self.install(installer, info, dest))

        dep_graph = DependencyGraph()
        for package in packages:
            for dependency, version_range in package.config['dependencies'].items():
                dep_graph.add(dependency, version_range)

        resolutions = dep_graph.resolve()
        for name, version_range in resolutions.items():
            max_version = version_range.max
            installer, info = self.find_installer(name, str(version_range))
            info.update({
                'version': max_version,
                'version_range': version_range
            })
            packages.append(self.install(installer, info, dest, save))

        for pkg in packages:
            dest = os.path.join(self.project.location, install_dir, pkg['name'])
            self.unstage(pkg, dest)
            success_message = 'Successfully installed {}'.format(pkg['name'])
            if pkg['version']:
                success_message += '@' + pkg['version']
            success_message += '!'
            self.cli.success(success_message)

        if save:
            self.cli.info('Saving to {}'.format(self.project['name']))
            self.project.save()

    def install(self, installer, info, dest, save=False):
        self.cli.info('Installing {}'.format(info.reference))
        info = installer.install(info, dest)

        try:
            new_package = PymPackage.load(info.path)
        except PymPackageException:
            self.cli.debug('No pym config file found, creating...')
            new_package = self.create_package(info)
            new_package.save()

        if save:
            self.project[self.packages_key][new_package['name']] = info.version_range

        return new_package

    def unstage(self, pkg, dest):
        """
        Unstage the package from the staging directory
        This will remove the package from the existing location, if there is one.
        :param pkg: {PymPackage} The package to unstage
        :param dest: {string} The full destination path to unstage the package
        :return: None
        """
        src = pkg.location
        self.cli.debug('Moving {src} to {dest}'.format(src=src, dest=dest))
        try:
            shutil.rmtree(dest)
        except FileNotFoundError:
            pass
        shutil.move(src, dest)

    def find_installer(self, name, version):
        try:
            for i in self.installers:
                info = i.can_install(name, version)
                if info is not None:
                    return i(self.cli), info
        except StopIteration as e:
            raise InstallerNotFoundException('Failed to find an installer for {}'.format(reference)) from e

    def find_ref_installer(self, reference):
        try:
            for i in self.installers:
                info = i.can_install_reference(reference)
                if info is not None:
                    return i(self.cli), info
        except StopIteration as e:
            raise InstallerNotFoundException('Failed to find an installer for {}'.format(reference)) from e

    def create_package(self, info):
        builder = PymConfigBuilder(self.cli)
        info.src = PackageInfo.guess_src(info)

        if info.src:
            config = builder.build(info)
        else:
            config = builder.query(info)

        new_package = PymPackage(info.path, config)
        return new_package


class PymInstaller(object):
    @classmethod
    def can_install(cls, name, version):
        """
        Checks to see if this installer can install the give name/reference
        :param name: {string} The ostensible name of the package
        :param reference: {string} The package install reference. This may be a git location, a version range, etc
        :return: {bool} True if this installer can install the give name/reference, False otherwise
        """
        raise NotImplemented("Function 'can_install' is not implemented in the base class")

    @classmethod
    def can_install_reference(cls, reference):
        raise NotImplemented("Function 'can_install_reference' is not implemented in the base class")

    def install(self, info, dest):
        """
        Install the given reference to the given destination
        :param reference: {string} A package reference
        :param dest:
        :param name:
        :return:
        """
        raise NotImplemented("Function 'install' is not implemented in the base class")

    def __init__(self, cli):
        self.cli = cli


class GitInstaller(PymInstaller):
    @classmethod
    def can_install(cls, name, version):
        info  = cls.can_install_reference(version)
        if info is not None:
            info.name = name
        return info

    @classmethod
    def can_install_reference(cls, reference):
        source, _, _ = reference.partition('#')
        if source.endswith('.git') or source.startswith('git+'):
            reference = re.sub(r"^git\+", "", reference)
            info = PackageInfo.parse(reference, delim='#')
            info.version_range = 'git+' + info.reference
            return info
        return None

    def install(self, info, dest):
        repo = self.clone(info.source, os.path.join(dest, info.name), info.version)
        try:
            version = str(repo.active_branch)
        except TypeError:
            # GitPython raises a TypeError on a detached HEAD state-- which is every time a tag is used
            # We'll just default to what we parsed
            version = info.version

        info.update({
            'path': repo.working_dir,
            'description': repo.description,
            'version': version
        })
        self.remove_git(info.path)
        return info

    def remove_git(self, path):
        git_dir = os.path.join(path, '.git')
        rmdir(git_dir)

    def clone(self, source, dest, version):
        repo = Repo.clone_from(source, dest)
        if version:
            self.cli.debug("Checking out {version}...".format(version=version))
            try:
                git = repo.git
                git.checkout(version)
            except exc.GitCommandError as e:
                raise VersionNotFoundException('Failed to find version {version}'.format(version=version)) from e
        return repo


class PypiInstaller(PymInstaller):
    URL = "https://pypi.python.org/pypi"

    @classmethod
    def can_install(cls, name, version):
        info = cls.can_install_reference(name)
        if info is not None:
            info.version = version
        return info

    @classmethod
    def can_install_reference(cls, reference):
        reference = re.sub(r"^pypi\+", "", reference)
        info = PackageInfo.parse(reference, delim='@')
        return info

    def install(self, info, dest):
        if info.version == None:
            info.version = self.find_max_version(info.name, info.version_range)

        url = self.find_download_url(info.name, info.version)
        wheel_path = pypi.download_file(url, dest)
        w = wheel.install.WheelFile(wheel_path)

        package_name = w.parsed_filename.group('name')
        version = w.parsed_filename.group('ver')
        dest = os.path.join(dest, package_name.lower())

        wheel_overrides = {'purelib': dest, 'platlib': dest}
        w.install(force=True, overrides=wheel_overrides)

        metadata_path = os.path.join(dest, w.distinfo_name, 'metadata.json')

        with open(metadata_path) as f:
            wheel_info = json.load(f)
            pkg_deps = self.parse_requires(wheel_info.get('run_requires'))
            info.update({'dependencies': pkg_deps})

        w.zipfile.close()
        os.remove(wheel_path)

        info.update({
            'path': dest,
            'version': version,
            'version_range': '^' + version
        })
        return info

    def find_max_version(self, package_name, version_range):
        """
        """
        previous = version_range.lower.version
        segments = ['major', 'minor', 'patch']
        seg_idx = 0
        current = copy.copy(previous)
        while seg_idx < len(segments):
            current.inc(segments[seg_idx])
            page = self.find_existing_page(package_name, current)
            if current not in version_range or page is None:
                current = copy.copy(previous)
                seg_idx += 1
            else:
                previous = copy.copy(current)
        return previous

    def find_existing_page(self, package_name, version):
        url = "{}/{}/{}".format(self.URL, package_name, version)
        page = requests.get(url)
        # Because pypi does not strictly enforce semver on packages, we end up with some packages that just leave of version segments
        while page.status_code != 200 and url.endswith('.0'):
            url = url.rstrip('.0')
            page = requests.get(url)
        if page.status_code != 200:
            page = None

        return page


    def find_download_url(self, package_name, version=""):
        """

        :param pacakge_name:
        :param version:
        :return:
        """
        page = self.find_existing_page(package_name, version)
        if page is None:
            raise PackageUrlException('Failed to fetch page for {}@{}'.format(package_name, version))
        soup = BeautifulSoup(page.content, 'html.parser')
        for link in soup.select('body a'):
            if link.string and link.string.endswith('.whl'):
                return link['href']
        raise PackageUrlException('Failed to find package for {}@{}'.format(package_name, version))

    def parse_requires(self, wheel_requires):
        """
        Ex: [
                {
                    "extra":"socks",
                    "requires": [
                        "PySocks (!=1.5.7,>=1.5.6)"
                    ]
                },
                {
                    "requires": [
                        "certifi (>=2017.4.17)",
                        "chardet (>=3.0.2,<3.1.0)",
                        "idna (>=2.5,<2.7)",
                        "urllib3 (<1.23,>=1.21.1)"
                    ]
                },
                {
                    "extra":"security",
                    "requires": [
                        "cryptography (>=1.3.4)",
                        "idna (>=2.0.0)",
                        "pyOpenSSL (>=0.14)"
                    ]
                },
                {
                    "environment":"sys_platform == \"win32\" and (python_version == \"2.7\" or python_version == \"2.6\")",
                    "extra":"socks",
                    "requires":[
                        "win-inet-pton"
                    ]
                }
            ]
        """
        wheel_requires = wheel_requires or []
        dependencies = {}
        for elem in wheel_requires:
            if elem.get('extra') is None and elem.get('environment') is None:
                requires = elem['requires']
                for requirement in requires:
                    package, _, version_range = requirement.partition(' ')
                    if not version_range:
                        version_range = '*'
                    else:
                        version_range = version_range.strip('()')
                        start, _, end = version_range.partition(',')
                        try:
                            if end:
                                upper, lower = sorted([semver.Comparator.parse(start), semver.Comparator.parse(end)])
                            else:
                                lower, upper = semver.Comparator.parse(start), None

                            version_range = semver.VersionRange(lower, upper)
                        except semver.VersionParseException as e:
                            self.cli.warn('Non-semantic version {}'.format(start))
                            version_range = start
                    dependencies[package] = str(version_range)

        return dependencies


class UninstallCommand(PymCommand):
    COMMAND = 'uninstall'

    @classmethod
    def args(cls, subparsers):
        subparser = subparsers.add_parser(UninstallCommand.COMMAND, help='Uninstall the specified package(s)',
                                          epilog='Example: pym uninstall --save tornado')
        subparser.add_argument('packages', help='Package name (or git location)', nargs='*', metavar='package')
        subparser.add_argument('--save', help='Save the removal to local config', action='store_true')

    @classmethod
    def make(cls, cli, args, path):
        project = PymPackage.load(path)
        return cls(cli, project)

    def __init__(self, cli, project):
        super(UninstallCommand, self).__init__(cli)
        self.project = project

    def run(self, args):
        removables = args['packages']
        save = args['save']
        install_dir = self.project['install_location']

        for removable in removables:
            location = os.path.join(self.project.location, install_dir, removable)
            self.cli.debug('Removing {} at {}'.format(removable, location))
            try:
                shutil.rmtree(location)
                if save:
                    del self.project['dependencies'][removable]
                self.cli.success('Uninstalled {removable}'.format(removable=removable))
            except FileNotFoundError as e:
                self.cli.warn('Failed to uninstall {}. Are you sure the name is spelled correctly?'.format(removable))
            except KeyError as e:
                self.cli.debug('{} was never saved as a dependency, but has been removed'.format(removable))
        self.project.save()


class DependencyGraph(object):
    """

    """
    def __init__(self):
        """
        """
        self.dependencies = collections.defaultdict(list)

    def add(self, name, version_range):
        """
        """
        self.dependencies[name].append(semver.VersionRange.parse(version_range))

    def resolve(self):
        resolutions = {}

        for name, ranges in self.dependencies.items():
            accepted_range = functools.reduce(lambda a, r: a.intersection(r), ranges)
            resolutions[name] = accepted_range
        return resolutions


def rmdir(dirpath):
    def handle_readonly(func, path, exc):
        excvalue = exc[1]
        if excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise exc[1]
    shutil.rmtree(dirpath, ignore_errors=False, onerror=handle_readonly)
