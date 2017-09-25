"""
Modeled after npm's semver module

semver.valid('1.2.3') // '1.2.3'
semver.valid('a.b.c') // null
semver.clean('  =v1.2.3   ') // '1.2.3'
semver.satisfies('1.2.3', '1.x || >=2.5.0 || 5.0.0 - 7.2.3') // true
semver.gt('1.2.3', '9.8.7') // false
semver.lt('1.2.3', '9.8.7') // true

https://github.com/npm/node-semver


Key philosophies:

1. A version is the basis of all operations, consisting of a major, minor, patch, and build value
2. A comparitor consists of an operator and a version
3. A version range consists of upper and lower comparitors
4. A spec consists of an arbitrary number of version ranges
"""

import re
import copy
from collections import OrderedDict


"""
Functions
"""


def valid(v):
    pass


def inc(v, release, identifier=None):
    pass


def prerelease(v):
    pass


def major(v):
    pass


def minor(v):
    pass


def patch(v):
    pass


def intersects(r1, r2):
    pass


def clean(v):
    pass


def satisfies(v, vrange):
    pass


"""
Comparison
"""


def eq(v1, v2):
    pass


def neq(v1, v2):
    pass


def gt(v1, v2):
    pass


def gte(v1, v2):
    pass


def lt(v1, v2):
    pass


def lte(v1, v2):
    pass


def match(a, b):
    return None


class Version(object):
    PRIMARY_SEGMENTS = ['major', 'minor', 'patch']

    def __init__(self, major=None, minor=None, patch=None, build=""):
        self.segments = OrderedDict({
            'major': major or 0,
            'minor': minor or 0,
            'patch': patch or 0,
            'build': build
        })
        self.partial = minor is None or patch is None

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and \
               self.patch == other.patch and self.build == other.build

    def __copy__(self):
        return Version(self.major, self.minor, self.patch, self.build)

    def __getitem__(self, item):
        return self.segments[item]

    def __setitem__(self, key, value):
        self.segments[key] = value

    def __str__(self):
        out = "{}.{}.{}".format(self.major, self.minor, self.patch)
        if self.build:
            out += "-" + build
        return out

    def __repr__(self):
        return "{}: {}".format(id(self), str(self))

    @property
    def major(self):
        return self['major']

    @property
    def minor(self):
        return self['minor']

    @property
    def patch(self):
        return self['patch']

    @property
    def build(self):
        return self['build']

    def inc(self, release, identifier=None):
        try:
            idx = Version.PRIMARY_SEGMENTS.index(release)
            remainder = Version.PRIMARY_SEGMENTS[idx+1:]
            for seg in remainder:
                self.segments[seg] = 0
            self.segments[release] += 1
        except ValueError as e:
            pass

    @classmethod
    def parse(cls, version_str):
        try:
            version_str = version_str.lstrip('=v')
            primary, _, build = version_str.partition('-')
            parts = iter(primary.split('.'))
            vmajor = int(next(parts))
            vminor = int(next(parts, 0)) or None
            vpatch = int(next(parts, 0)) or None
            return cls(vmajor, vminor, vpatch, build)
        except ValueError as e:
            raise VersionParseException('Invalid version string {}'.format(version_str)) from e


class Comparator(object):
    def __init__(self, operator, version):
        self.operator = operator
        self.version = version

    def intersects(self, other):
        pass

    @classmethod
    def parse(cls, v):
        m = re.search(r'(<=|<|>=|>)', v)
        if m is not None:
            op = m.group(0)
            version = v.lstrip(op)
        else:
            op = '='
            version = v
        return Comparator(op, Version.parse(version))


class VersionRange(object):
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __contains__(self, item):
        pass

    def max(self, versions):
        pass

    def min(self, versions):
        pass

    def greater(self, version):
        pass

    def lesser(self, version):
        pass

    @staticmethod
    def valid(v):
        pass

    @classmethod
    def parse(cls, v):
        lower, _, upper = v.partition(' - ')
        if upper:
            return HyphenRange.parse(v)

        lower, _, upper = v.partition(' ')
        if upper:
            return cls(Comparator.parse(lower), Comparator.parse(upper))

        if any(x in v.split('.') for x in ('*', 'x', 'X')):
            return XRange.parse(v)

        if v.startswith('~'):
            return TildeRange.parse(v)

        if v.startswith('^'):
            return CaretRange.parse(v)


class HyphenRange(VersionRange):
    @classmethod
    def parse(cls, v):
        lower, _, upper = v.partition(' - ')
        lower = Comparator('>=', Version.parse(lower))
        vupper = Version.parse(upper)
        op = '<' if vupper.partial else '<='
        upper = Comparator(op, vupper)
        return cls(lower, upper)


class XRange(VersionRange):
    @classmethod
    def parse(cls, v):
        vlower = Version()
        vupper = Version()
        previous = None
        segs = iter(Version.PRIMARY_SEGMENTS)
        for piece in v.split('.'):
            if piece in ('*', 'x', 'X'):
                if previous is not None:
                    vupper[previous] += 1
                    upper = Comparator('<', vupper)
                else:
                    upper = None
                lower = Comparator('>=', vlower)
                return cls(lower, upper)
            else:
                previous = next(segs)
                vlower[previous] = int(piece)
                vupper[previous] = int(piece)
        raise VersionParseException("Failed to parse '{}'".format(v))


class TildeRange(VersionRange):
    @classmethod
    def parse(cls, v):
        vlower = Version.parse(v.lstrip('~'))
        lower = Comparator('>=', vlower)
        vupper = copy.copy(vlower)
        if vupper.minor or vupper.patch:
            vupper.inc('minor')
        else:
            vupper.inc('major')
        upper = Comparator('<', vupper)
        return cls(lower, upper)


class CaretRange(VersionRange):
    @classmethod
    def parse(cls, v):
        vlower = Version.parse(v.lstrip('^'))
        lower = Comparator('>=', vlower)
        vupper = Version()
        for attr, x in vlower.segments.items():
            if x != 0:
                vupper[attr] = vlower[attr] + 1
                break
        return cls(lower, Comparator('<', vupper))


class Spec(object):
    def __init__(self, ranges):
        self.ranges = ranges

    @classmethod
    def parse(cls, spec):
        ranges = [VersionRange.parse(v) for v in spec.split(' or ')]
        return cls(ranges)


class SemverException(Exception):
    pass


class VersionParseException(SemverException):
    pass


class RangeParseException(SemverException):
    pass
