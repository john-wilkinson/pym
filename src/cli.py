import os
import sys
from collections import namedtuple


if os.name == 'nt':
    from . import winapi


def make():
    if os.name == 'nt':
        return Win32Cli()
    else:
        return PymCli()


class PymCli(object):
    """
    The PymCli class is used to abstract any interactions with the user (input and output)
    """

    def __init__(self):
        self.out = sys.stdout
        self.err = sys.stderr

    def info(self, message):
        self.write('info', message)

    def success(self, message):
        self.write('success', message)

    def action(self, message):
        self.write('action', message)

    def warning(self, message):
        self.write('warning', message)

    def error(self, message):
        self.write('error', message, self.err)

    def debug(self, message):
        self.write('debug', message)

    def write(self, level, message, stream=None):
        stream = stream or self.out
        stream.write("[{level}] {message}{newline}".format(level=level, message=message, newline=os.linesep))

    def ask(self, question):
        return input(question)


class Win32Cli(PymCli):
    COLOR_MAP = {
        'info': winapi.FOREGROUND_CYAN,
        'success': winapi.FOREGROUND_GREEN,
        'action': winapi.FOREGROUND_MAGENTA,
        'warning': winapi.BACKGROUND_YELLOW,
        'error': winapi.FOREGROUND_RED,
        'debug': winapi.FOREGROUND_BLUE
    }

    FOREGROUND = winapi.FOREGROUND_GREY
    BACKGROUND = winapi.BACKGROUND_BLACK
    NEWLINE = os.linesep

    def write(self, level, message, stream=None):
        stream = stream or self.out
        self.write_level(level, stream)
        stream.write(message + Win32Cli.NEWLINE)

    def write_level(self, level, stream):
        color = Win32Cli.COLOR_MAP[level]
        winapi.set_text_attr(color | Win32Cli.BACKGROUND | winapi.FOREGROUND_INTENSITY )
        stream.write("[{level}] {spacing}".format(level=level, spacing=self.spacing(level)))
        stream.flush()
        winapi.set_text_attr(Win32Cli.FOREGROUND | Win32Cli.BACKGROUND)

    def spacing(self, level):
        return " " * (7 - len(level))
