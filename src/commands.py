import os
import shutil
import errno
import stat
import sys
import inspect
import itertools
from git import Repo, exc
from .package import PymPackage, PymConfigBuilder, PackageInfo, PymPackageException


def make():
    return {
        InitCommand.COMMAND: InitCommand,
        InstallCommand.COMMAND: InstallCommand
    }


class InstallerNotFoundException(Exception):
    """
    Raised when an installer cannot be found for the specified source
    """


class VersionNotFoundException(Exception):
    """
    Raised when the specified version cannot be found
    """


class PymCommand(object):
    """
    Base class for create pym command objects
    Property "Command" is used for registering commands
    """
    COMMAND = None

    @classmethod
    def args(cls, subparsers):
        """
        Used to attach related argument structure to the pym subcommands
        Ex:
        subparser = subparsers.add_parser(MyCommand.COMMAND, help='Do things',
                                          epilog='More information')
        See argparse docs for more detail:
            https://docs.python.org/3.6/library/argparse.html#sub-commands
        :param subparser: {argparse.ArgumentParser}
            https://docs.python.org/3.6/library/argparse.html#argparse.ArgumentParser
        :return: None
        """
        raise NotImplemented("Method 'args' not implemented in base class")

    def __init__(self, cli):
        """
        Initialize a PymCommand
        :param log: {logging.PymLogger} A logger instance
        """
        self.cli = cli

    def run(self, args, path):
        """
        Run the subcommand.
        :param args: {dict} Command line arguments, as parsed by argparse, converted to a dict
        :return: None
        """
        raise NotImplemented("Method 'run' not implemented in base class")


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
        subparser = subparsers.add_parser(InstallCommand.COMMAND, help='Install the specified package',
                                          epilog='Example: pym install --save https://github.com/tornadoweb/tornado.git')
        subparser.add_argument('packages', help='Package name (or git location)', nargs='*', metavar='package')
        subparser.add_argument('--save', help='Save the package to local config', action='store_true')

    def __init__(self, cli):
        super(InstallCommand, self).__init__(cli)
        self.installers = [
            GitInstaller
        ]

        self.project = None
        self.packages_key = 'dependencies'

    def run(self, args, path):
        self.project = PymPackage.load(path)

        if args['packages']:
            installables = list(itertools.zip_longest([], set(args['packages'])))
        else:
            installables = self.project[self.packages_key].items()

        self.cli.debug(installables)

        dest = os.path.join(path, self.project['staging_location'])

        packages = []

        for name, reference in installables:
            packages.append(self.install(reference, dest, args['save'], name))

        for pkg in packages:
            dest = os.path.join(self.project.location, self.project['install_location'], pkg['name'])
            self.unstage(pkg, dest)
            self.cli.success('Successfully installed {}!'.format(pkg['name']))

        if args['save']:
            self.cli.info('Saving to {}'.format(self.project['name']))
            self.project.save()

    def install(self, reference, dest, save=False, name=None):
        self.cli.info('Installing {}'.format(reference))
        installer = self.find_installer(name, reference)
        info = installer.install(reference, dest, name)

        try:
            new_package = PymPackage.load(info.path)
        except PymPackageException:
            self.cli.info('No pym config file found, creating...')
            new_package = self.create_package(info)
            new_package.save()

        if save:
            self.project[self.packages_key][new_package['name']] = info.version_range

        return new_package

    def unstage(self, pkg, dest):
        src = pkg.location
        self.cli.debug('Moving {src} to {dest}'.format(src=src, dest=dest))
        try:
            shutil.rmtree(dest)
        except FileNotFoundError:
            pass
        shutil.move(src, dest)

    def find_installer(self, name, reference):
        try:
            cls = next(i for i in self.installers if i.can_install(name, reference))
            return cls(self.cli)
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


class GitInstaller(object):
    @classmethod
    def can_install(cls, name, reference):
        source, _, _ = reference.partition('#')
        return source.endswith('.git') or source.startswith('git+')

    def __init__(self, cli):
        self.cli = cli

    def install(self, reference, dest, name=None):
        info = PackageInfo.parse(reference.lstrip('git+'), delim='#')
        info.name = name or info.name
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
            'version': version,
            'version_range': 'git+' + reference
        })
        self.remove_git(info.path)
        return info

    def remove_git(self, path):
        def handle_readonly(func, path, exc):
            excvalue = exc[1]
            if excvalue.errno == errno.EACCES:
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
                func(path)
            else:
                raise exc[1]

        git_dir = os.path.join(path, '.git')
        shutil.rmtree(git_dir, ignore_errors=False, onerror=handle_readonly)

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


class InitCommand(PymCommand):
    COMMAND = 'init'

    @classmethod
    def args(cls, subparsers):
        subparsers.add_parser(InitCommand.COMMAND, help='Initialize a pym project in the current directory',
                                          epilog='Example: pym init')

    def run(self, args, path):
        info = PackageInfo.parse(path)
        info.path = path
        info.src = PackageInfo.guess_src(info)
        info.version = '0.1.0'
        info.license = 'MIT'
        builder = PymConfigBuilder(self.cli)
        config = builder.query(info)
        project = PymPackage(path, config)
        project.save()
        self.cli.success('Initialized project')

