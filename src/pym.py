import os
import sys
import json
import argparse
import commands
import package


class Pym(object):

    def run(self):
        command_registry = commands.make()
        args = self.get_args(command_registry)

        config = self.load_config()
        cmd = command_registry[args['command']](config)

        cmd.run(args)

    def get_args(self, command_registry):
        parser = argparse.ArgumentParser(prog='pym.py', description='Manage Python packages.')
        subparsers = parser.add_subparsers(help='pym sub-commands', dest='command')

        for _, cls in command_registry.items():
            cls.args(subparsers)

        args = vars(parser.parse_args())

        if not args['command']:
            parser.print_help()
            sys.exit(2)
        return args

    def load_config(self):
        location = os.path.realpath(os.path.join(os.getcwd()))

        project = package.PymPackage(location)
        project.path = location
        try:
            config = project.config
        except package.PymPackageException as e:
            print(str(e))
            print("Run 'pym init' to create a project here")
            sys.exit(2)

        return config


if __name__ == "__main__":
    (Pym()).run()
