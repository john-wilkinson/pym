import os
import shutil
import errno
import stat
import sys
import inspect
from git import Repo
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
    COMMAND = 'install'

    @classmethod
    def args(cls, subparsers):
        subparser = subparsers.add_parser(InstallCommand.COMMAND, help='Install the specified package',
                                          epilog='Example: pym install --save https://github.com/tornadoweb/tornado.git')
        subparser.add_argument('package', help='Package name (or git location)')
        subparser.add_argument('--save', help='Save the package to local config', action='store_true')

    def __init__(self, cli):
        super(InstallCommand, self).__init__(cli)
        self.installers = [
            GitInstaller
        ]

    def run(self, args, path):
        project = PymPackage.load(path)

        dest = os.path.join(path, project['install_location'])
        reference = args['package']

        installer = self.find_installer(reference)
        self.cli.info('Installing {}'.format(reference))

        info = installer.install(reference, os.path.join(path, dest))

        try:
            new_package = PymPackage.load(info.path)
        except PymPackageException:
            self.cli.info('No pym config file found, creating...')
            new_package = self.create_package(info)
            new_package.save()

        if args['save']:
            self.cli.info('Saving to {}'.format(project['name']))
            project['dependencies'][info.name] = info.version_range
            project.save()
        self.cli.success('Successfully installed {}!'.format(new_package['name']))

    def find_installer(self, reference):
        try:
            cls = next(i for i in self.installers if i.can_install(reference))
            return cls()
        except StopIteration as e:
            raise InstallerNotFoundException('Failed to find an installer for {}'.format(reference)) from e

    def create_package(self, info):
        builder = PymConfigBuilder()
        info.src = PackageInfo.guess_src(info)

        if info.src:
            config = builder.build(info)
        else:
            config = builder.query(info)

        new_package = PymPackage(info.path, config)
        return new_package


class GitInstaller(object):
    @classmethod
    def can_install(cls, source):
        return source.endswith('.git')

    def install(self, reference, dest):
        info = PackageInfo.parse(reference, delim='#')
        repo = self.clone(info.source, os.path.join(dest, info.name))
        info.update({
            'path': repo.working_dir,
            'description': repo.description,
            'version': str(repo.active_branch),
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

    def clone(self, source, dest):
        return Repo.clone_from(source, dest)


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

