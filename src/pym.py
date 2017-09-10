import os
import sys
import json
from . import argparse
from . import commands
from . import package


class Pym(object):

    def run(self):
        command_registry = commands.make()
        args = self.get_args(command_registry)

        cmd = command_registry[args['command']]()

        location = os.path.realpath(os.path.join(os.getcwd()))

        with PymCommandContext():
            cmd.run(args, location)

    def get_args(self, command_registry):
        parser = argparse.ArgumentParser(prog='pym', description='Manage Python packages.')
        subparsers = parser.add_subparsers(help='pym sub-commands', dest='command')

        for _, cls in command_registry.items():
            cls.args(subparsers)

        args = vars(parser.parse_args())

        if not args['command']:
            parser.print_help()
            sys.exit(2)
        return args


class PymCommandContext(object):
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type == package.PymPackageException:
            print(str(exc_val))
            print("Run 'pym init' to create a project here")
            sys.exit(2)


def go():
    (Pym()).run()


if __name__ == "__main__":
    go()
