import os
import sys
import json
import argparse
from . import commands
from . import package
from . import cli


class PymApp(object):

    def __init__(self, cli):
        self.cli = cli

    def run(self):
        registry = commands.CommandRegistry()
        args = self.args(registry)

        self.cli.enable_debug = args['debug']
        location = os.path.realpath(os.path.join(os.getcwd()))

        with commands.PymCommandContext(self.cli):
            cmd = registry.make(args['command'], self.cli, args, location)
            cmd.run(args)

    def args(self, registry):
        parser = argparse.ArgumentParser(prog='pym', description='Manage Python packages.')
        parser.add_argument('--debug', help='Run with debug output enabled', action='store_false')

        registry.args(parser)
        args = vars(parser.parse_args())

        if not args['command']:
            parser.print_help()
            sys.exit(2)
        return args


def go():
    (PymApp(cli.make())).run()


if __name__ == "__main__":
    go()
