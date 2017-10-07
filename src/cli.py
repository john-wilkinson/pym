import os
import sys
from collections import namedtuple


class PymCli(object):
    """
    The PymCli class is used to abstract any interactions with the user (input and output)
    """
    def __init__(self, debug=False):
        self.out = sys.stdout
        self.err = sys.stderr
        self.enable_debug = debug

    def info(self, message):
        self.write('info', message)

    def success(self, message):
        self.write('success', message)

    def action(self, message):
        self.write('action', message)

    def warn(self, message):
        self.write('warning', message)

    def error(self, message):
        self.write('error', message, self.err)

    def debug(self, message):
        if not self.debug:
            self.write('debug', message)

    def write(self, level, message, stream=None):
        stream = stream or self.out
        stream.write("[{level}] {message}{newline}".format(level=level, message=str(message), newline=os.linesep))

    def ask(self, question):
        return input(question)

    def spacing(self, level):
        return " " * (8 - len(level))


if os.name == 'nt':
    from . import winapi

    class Win32Cli(PymCli):
        COLOR_MAP = {
            'info': winapi.FOREGROUND_CYAN,
            'success': winapi.FOREGROUND_GREEN,
            'action': winapi.FOREGROUND_MAGENTA,
            'warning': winapi.FOREGROUND_YELLOW,
            'error': winapi.FOREGROUND_RED,
            'debug': winapi.FOREGROUND_BLUE
        }

        FOREGROUND = winapi.FOREGROUND_GREY
        BACKGROUND = winapi.BACKGROUND_BLACK
        NEWLINE = os.linesep

        def write(self, level, message, stream=None):
            stream = stream or self.out
            self.write_level(level, stream)
            stream.write(str(message) + Win32Cli.NEWLINE)

        def write_level(self, level, stream):
            color = Win32Cli.COLOR_MAP[level]
            winapi.set_text_attr(color | Win32Cli.BACKGROUND | winapi.FOREGROUND_INTENSITY)
            stream.write("[{level}] {spacing}".format(level=level, spacing=self.spacing(level)))
            stream.flush()
            winapi.set_text_attr(Win32Cli.FOREGROUND | Win32Cli.BACKGROUND)


def make():
    if os.name == 'nt':
        return Win32Cli()
    else:
        return Vt100Cli()


class Vt100Cli(PymCli):
    COLORS = {
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m'
    }

    LEVEL_COLORS = {
        'info': 'cyan',
        'success': 'green',
        'action': 'magenta',
        'warning': 'yellow',
        'error': 'red',
        'debug': 'blue'
    }

    END_SEQ = '\033[0m'

    def write(self, level, message, stream=None):
        stream = stream or self.out
        color = Vt100Cli.COLORS[Vt100Cli.LEVEL_COLORS[level]]
        end = Vt100Cli.END_SEQ
        spacing = self.spacing(level)
        stream.write("{color}[{level}]{end}{spacing}{message}{newline}"
                     .format(level=level, message=str(message), newline=os.linesep, color=color, end=end,
                             spacing=spacing))
        stream.flush()
