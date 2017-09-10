import os
import json


class PymPackageException(Exception):
    """
    Raised when not a PymPackage
    """


class PymPackage(object):
    def __init__(self, reference):
        self.reference = reference
        self.source, _, self.version = self.reference.partition('@')
        self.name = os.path.splitext(os.path.basename(self.source))[0]

        self.config_filename = 'pym.json'

        self.path = None
        self.description = None
        self._config = None

    @property
    def config(self):
        if self._config:
            return self._config

        try:
            with open(self.config_path) as data:
                config = json.load(data)
        except FileNotFoundError:
            raise PymPackageException('Failed to find {} in {}'.format(self.config_filename, self.source))

        return config

    @config.setter
    def config(self, val):
        self._config = val
        with open(self.config_path, "w") as f:
            f.write(json.dumps(val, indent=4))

    @property
    def config_path(self):
        return os.path.join(self.path, self.config_filename)


class PymConfigCreator(object):
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
                value = input(question)
            config[field] = value

        return config
