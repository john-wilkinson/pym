import os
import json


class PymPackageException(Exception):
    """
    Raised when not a PymPackage
    """


class PymPackage(object):
    def __init__(self, reference):
        self.reference = reference
        self.path = reference
        self.source, _, self.version = self.reference.partition('@')
        self.name = os.path.splitext(os.path.basename(self.source))[0]

        self.config_filename = 'pym.json'

        self.version_range = None
        self.description = None
        self.config = None

    def load_config(self, force=False):
        if self.config and not force:
            return self.config

        try:
            with open(self.config_path) as data:
                self.config = json.load(data)
        except FileNotFoundError:
            raise PymPackageException('Failed to find {} in {}'.format(self.config_filename, self.path))

        return self.config

    def save_config(self, config=None):
        if config is not None:
            self.config = config
        with open(self.config_path, "w") as f:
            f.write(json.dumps(self.config, indent=4))

    @property
    def config_path(self):
        return os.path.join(self.path, self.config_filename)


class PymConfigCreator(object):
    DEFAULT_CONFIG = {
        'name': '',
        'version': '',
        'description': '',
        'packages': {}
    }

    def __init__(self, required_fields=None):
        if required_fields is None:
            required_fields = {
                'name': "Project name",
                'description': "Project description",
                'version': "Project version",
                'src': "Project source location"
            }
        self.required_fields = required_fields

    def create(self, use_suggestions=False, **suggestions):
        config = {}

        for field, desc in self.required_fields.items():
            suggestion = suggestions.get(field)
            if use_suggestions and suggestion:
                value = suggestion
            else:
                question = "{} ({})? ".format(desc, suggestion) if suggestion else "{}? ".format(desc)
                value = input(question) or suggestion or ""
            config[field] = value

        config = {**PymConfigCreator.DEFAULT_CONFIG, **config}
        return config
