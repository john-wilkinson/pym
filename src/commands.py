import os
import shutil
import errno
import stat
import sys
import inspect
import itertools

from . import exceptions
from . import package


class CommandRegistry(object):
    def __init__(self):
        from .install import InstallCommand, UninstallCommand

        self.commands = {
            InitCommand.COMMAND: InitCommand,
            InstallCommand.COMMAND: InstallCommand,
            UninstallCommand.COMMAND: UninstallCommand
        }

    def make(self, command, args, cli, location):
        """
        Create command object specified by the command argument
        :param command: {string} The command object to create
        :param args: {dict} The command line parameters
        :param cli: {cli.PymCli} The cli interface object
        :param location: {string} The current execution location
        :return: {PymCommand} An instance of a pym command
        """
        cls = self.commands[command]
        return cls.make(args, cli, location)

    def args(self, parser):
        """
        Attaches args to the given parser
        :param parser: {argparse.ArgumentParser} An argparse ArgumentParser instance
        :return: None
        """
        subparsers = parser.add_subparsers(help='pym sub-commands', dest='command')

        for _, cls in self.commands.items():
            cls.args(subparsers)


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

    @classmethod
    def make(cls, cli, args, location):
        """
        Used to create this command
        :param cli: {cli.PymCli} Reference to cli object for input and output
        :param args: {dict} Dictionary of command line arguments
        :param location: {string} Current execution/project location
        :return: {PymCommand} Returns an instance of the invoked PymCommand class
        """
        raise NotImplemented("Method 'make' not implemented in base class")

    def __init__(self, cli):
        """
        Initialize a PymCommand
        :param log: {cli.PymClie} Reference to cli object for input and output
        """
        self.cli = cli

    def run(self, args):
        """
        Run the subcommand.
        :param args: {dict} Command line arguments, as parsed by argparse, converted to a dict
        :return: None
        """
        raise NotImplemented("Method 'run' not implemented in base class")

    def cleanup(self):
        pass


class PymCommandContext(object):
    ACTIONS = {
        exceptions.PymPackageException: "Run 'pym init' to create a project here",
        exceptions.InstallerNotFoundException: "Double-check the installation source and version"
                                               "(use '#' for git instead of '@')",
        exceptions.VersionNotFoundException: "Please check that the version specified exists",
        exceptions.PackageUrlException: "Please make sure the package and version exist"
    }

    def __init__(self, cli, cmd_name, args, location):
        self.cli = cli
        self.cmd_name = cmd_name
        self.args = args
        self.location = location

    def __enter__(self):
        registry = CommandRegistry()
        self.cmd = registry.make(self.cmd_name, self.cli, self.args, self.location)
        return self.cmd

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and exc_type in PymCommandContext.ACTIONS:
            self.cli.error(str(exc_val))
            self.cli.action(PymCommandContext.ACTIONS[exc_type])
            sys.exit(2)
        self.cmd.cleanup()


class InitCommand(PymCommand):
    COMMAND = 'init'

    @classmethod
    def args(cls, subparsers):
        subparsers.add_parser(InitCommand.COMMAND, help='Initialize a pym project in the current directory',
                              epilog='Example: pym init')

    @classmethod
    def make(cls, cli, args, location):
        info = package.PackageInfo.parse(location)
        info.path = location
        info.src = package.PackageInfo.guess_src(info)
        info.version = '0.1.0'
        info.license = 'MIT'
        return cls(cli, info)

    def __init__(self, cli, info):
        super(InitCommand, self).__init__(cli)
        self.info = info

    def run(self, args):
        project = self.create(self.info)
        project.save()
        self.cli.success('Initialized project')

    def create(self, info):
        builder = package.PymConfigBuilder(self.cli)
        config = builder.query(info)
        project = package.PymPackage(info.path, config)
        return project
