import os
import json


class PymPackageException(Exception):
    """
    Raised when not a PymPackage
    """


DEFAULT_VALUES = {
    'staging_location': os.path.join('pym_packages', '.staging'),
    'install_location': 'pym_packages'
}


DEFAULT_CONFIG = {
    'name': '',
    'version': '0.1.0',
    'description': '',
    'src': 'src',
    'license': 'MIT',
    'dependencies': {},
}


class PymConfigBuilder(object):
    FIELDS = {
        'name': "Project name",
        'description': "Project description",
        'version': "Project version",
        'src': "Project source sub-directory (ex: 'src')",
        'license': "Project license (ex: MIT, GPLv2, etc)"
    }

    def __init__(self, cli=None):
        self.cli = cli

    def build(self, values):
        config = {key: values.get(key) or val for key, val in DEFAULT_CONFIG.items()}
        return config

    def query(self, suggestions):
        values = {}

        for field, desc in PymConfigBuilder.FIELDS.items():
            suggestion = suggestions.get(field)
            question = "{} ({})? ".format(desc, suggestion) if suggestion else "{}? ".format(desc)
            values[field] = self.cli.ask(question) or suggestion or ""

        return self.build(values)


class PackageInfo(dict):
    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        self[key] = value

    @classmethod
    def parse(cls, reference, delim='@'):
        source, _, version = reference.partition(delim)
        name = os.path.splitext(os.path.basename(source))[0]
        return PackageInfo(
            reference=reference,
            name=name,
            version=version,
            source=source
        )

    @staticmethod
    def guess_src(info, suffixes=None):
        suffixes = suffixes or ['src', info.name]
        for suffix in suffixes:
            guess = os.path.join(info.path, suffix)
            if os.path.exists(guess):
                return os.path.relpath(guess, info.path)

        return None


class PymPackage(object):
    def __init__(self, location, config):
        self.location = location
        self.config = config

    def __getitem__(self, item):
        return self.config[item]

    def __setitem__(self, key, value):
        self.config[key] = value

    def save(self):
        with open(PymPackage.config_path(self.location), "w") as f:
            f.write(json.dumps(self.config, indent=4))

    @classmethod
    def load(cls, location):
        path = PymPackage.config_path(location)
        try:
            with open(path) as data:
                config = json.load(data)
                return PymPackage(location, {**DEFAULT_VALUES, **config})
        except FileNotFoundError as e:
            raise PymPackageException('Failed to find load config file {}'.format(path)) from e

    @staticmethod
    def config_path(location):
        return os.path.join(location, 'pym.json')
