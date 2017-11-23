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
import stat
import errno
import shutil
import itertools
import wheel.install
from git import Repo, exc

### DEBUG
import psutil

from . import pypi
from .commands import PymCommand
from .package import PymPackage, PymConfigBuilder, PackageInfo
from .exceptions import InstallerNotFoundException, VersionNotFoundException, PymPackageException



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

        packages = []

        for installer, info in installables:
            packages.append(self.install(installer, info, dest))

        for pkg in packages:
            dest = os.path.join(self.project.location, install_dir, pkg['name'])
            self.unstage(pkg, dest)
            self.cli.success('Successfully installed {}!'.format(pkg['name']))

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
        url = pypi.find_download_url(info.name, info.version)
        wheel_path = pypi.download_file(url, dest)
        w = wheel.install.WheelFile(wheel_path)
        package_name, _, version = w.datadir_name.partition('-')
        version = version.rstrip('.data')
        dest = os.path.join(dest, package_name)

        wheel_overrides = {'purelib': dest, 'platlib': dest}
        w.install(force=True, overrides=wheel_overrides)
        w.zipfile.close()
        os.remove(wheel_path)

        info.update({
            'path': dest,
            'version': version,
            'version_range': version
        })
        return info


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
    def __init__(self, node):
        """

        :param node:
        """


def rmdir(dirpath):
    def handle_readonly(func, path, exc):
        excvalue = exc[1]
        if excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise exc[1]
    shutil.rmtree(dirpath, ignore_errors=False, onerror=handle_readonly)
