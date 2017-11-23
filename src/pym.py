import os
import sys
import json
import argparse
from . import commands
from . import package
from . import cli


class PymApp(object):

    def __init__(self):
        self.cli = None

    def run(self):
        registry = commands.CommandRegistry()
        args = self.args(registry)

        self.cli = cli.make(args['debug'])
        location = os.path.realpath(os.path.join(os.getcwd()))

        with commands.PymCommandContext(self.cli):
            cmd = registry.make(args['command'], self.cli, args, location)
            cmd.run(args)

    def args(self, registry):
        parser = argparse.ArgumentParser(prog='pym', description='Manage Python packages.')
        parser.add_argument('-d', '--debug', help='Run with debug output enabled', action='store_true')

        registry.args(parser)
        args = vars(parser.parse_args())

        if not args['command']:
            parser.print_help()
            sys.exit(2)
        return args


def go():
    (PymApp()).run()


if __name__ == "__main__":
    go()
