import sys
import imp
import json
import os


class PymLoadException(ImportError):
    """
    Raised when the specified module could not be loaded
    """


class PymLoader(object):
    def __init__(self, config=None):
        self.location = os.path.realpath(os.path.join(os.getcwd()))
        if not config:
            try:
                with open(os.path.join(self.location, 'pym.json')) as data:
                    config = json.load(data)
            except FileNotFoundError:
                config = {}

        self.config = config
        self.dependency_dir = config.get('install_location', 'packages')

        self.loaded = {}

    def find_module(self, fullname, path=None):
        package_path = self.calculate_path(fullname)

        if package_path and os.path.exists(package_path):
            return self
        else:
            return None

    def calculate_path(self, fullname):
        segments = fullname.split('.')

        if not len(segments):
            return None

        package_name = segments.pop(0)
        partial_path = os.path.join(self.location, self.dependency_dir, package_name)

        if not os.path.exists(partial_path):
            return None

        suffix = os.path.sep.join(segments)

        with open(os.path.join(partial_path, 'pym.json')) as data:
            package_config = json.load(data)

        package_src = package_config['src']

        package_path = os.path.join(partial_path, package_src, suffix)
        return package_path

    def load_module(self, fullname):
        try:
            return sys.modules[fullname]
        except KeyError:
            pass

        if fullname in self.loaded:
            return self.loaded[fullname]

        package_path = self.calculate_path(fullname)

        package = self.create_module(fullname, package_path)

        self.loaded[fullname] = package
        return package

    def create_module(self, name, path):
        if os.path.isdir(path):
            path = os.path.join(path, '__init__.py')
        else:
            path += '.py'

        if not os.path.isfile(path):
            raise PymLoadException('Failed to load module {}, maybe you are missing an __init__.py?'.format(name))

        m = imp.load_source(name, path)

        return m
