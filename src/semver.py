
def match(a, b):
    return None


class Version(object):
    def __init__(self, major='0', minor='0', patch='0', build=""):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.build = build

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and \
               self.patch == other.patch and self.build == other.build

    def __iter__(self):
        yield major
        yield minor
        yield patch
        yield build

    def match(self, other):
        if self == other:
            return True
        return Version.match_segment(self.major, other.major) and Version.match_segment(self.minor, other.minor) and \
               Version.match_segment(self.patch, other.patch) and Version.match_segment(self.build, other.build)

    @property
    def specificity(self):
        specificity = 0
        multiplier = 1000
        for seg in [self.major, self.minor, self.patch]:
            if seg == '*':
                val = 1
            elif seg.startswith('^'):
                val = 2
            else:
                val = 3
            specificity += val * multiplier
            multiplier /= 10
        if self.build:
            specificity += 5
        return int(specificity)

    @staticmethod
    def match_segment(a, b):
        if a == b:
            return True
        if a == '*' or b == '*':
            return True

    @classmethod
    def parse(cls, version_str):
        primary, _, build = version_str.partition('-')
        parts = iter(primary.split('.'))
        major = next(parts, '0')
        minor = next(parts, '0')
        patch = next(parts, '0')
        return cls(major, minor, patch, build)


class Spec(object):
    def __init__(self, versions):
        self.versions = versions

    def __len__(self):
        return len(self.versions)

    def __getitem__(self, item):
        return self.versions[item]

    def __eq__(self, other):
        if len(self) != len(other):
            return false
        for i in range(len(self)):
            if self[i] != other[i]:
                return False
        return True

    def intersection(self, v):
        spec = Spec.parse(v)
        matches = []
        for v1 in self:
            for v2 in spec:
                if v1.match(v2):
                    matches.append(v1)
        return Spec(matches)

    @classmethod
    def parse(cls, version_range):
        versions = [Version.parse(v) for v in version_range.split(' or ')]
        return cls(versions)
