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
2. A comparator consists of an operator and a version (npm semver "Comparator")
3. A version range consists of upper and lower comparators (npm semver "Comparator Set")
4. A spec consists of an arbitrary number of version ranges (npm semver "Version Range")
"""

import re
import copy
from functools import total_ordering
from collections import OrderedDict


"""
Functions
"""


def valid(v):
    try:
        return Version.parse(v)
    except VersionParseException as e:
        return None


def inc(v, release, identifier=None):
    """
    @param v: {string}
    @param release: {string}
    @param identifier: {string}
    """
    version = Version.parse(v)
    version.inc(release, identifier)
    return version


def major(v):
    return Version.parse(v).major


def minor(v):
    return Version.parse(v).minor


def patch(v):
    return Version.parse(v).patch


def prerelease(v):
    return Version.parse(v).prerelease


def intersects(r1, r2):
    vrange = VersionRange.parse(r1)
    return vrange.intersects(VersionRange.parse(r2))


def clean(v):
    Version.clean(v)


def satisfies(v, cmp):
    c = Comparator.parse(cmp)
    return c.satisfies(Version.parse(v))


"""
Comparison
"""


def eq(v1, v2):
    return Version.parse(v1) == Version.parse(v2)


def neq(v1, v2):
    return Version.parse(v1) != Version.parse(v2)


def gt(v1, v2):
    return Version.parse(v1) > Version.parse(v2)


def gte(v1, v2):
    return Version.parse(v1) >= Version.parse(v2)


def lt(v1, v2):
    return Version.parse(v1) < Version.parse(v2)


def lte(v1, v2):
    return Version.parse(v1) <= Version.parse(v2)


def sort(v_list, reverse=False):
    return sorted(map(Version.parse, v_list), reverse=reverse)


"""
Ranges
"""


def valid_range(r):
    try:
        return VersionRange.parse(r)
    except VersionParseException:
        return None


def contains(r, v):
    vrange = VersionRange.parse(r)
    return v in vrange


def range_max(r, v):
    vrange = VersionRange.parse(r)
    versions = sort(v, reverse=True)
    for version in versions:
        if version in vrange:
            return version
    return None


def range_min(r, v):
    vrange = VersionRange.parse(r)
    versions = sort(v)
    for version in versions:
        if version in vrange:
            return version
    return None


@total_ordering
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
        return str(self) == str(other)

    def __lt__(self, other):
        for seg in self.segments:
            if self[seg] < other[seg]:
                return True
            elif self[seg] > other[seg]:
                return False
        return False

    def __copy__(self):
        return Version(self.major, self.minor, self.patch, self.build)

    def __getitem__(self, item):
        return self.segments[item]

    def __setitem__(self, key, value):
        self.segments[key] = value

    def __str__(self):
        out = "{}.{}.{}".format(self.major, self.minor, self.patch)
        if self.build:
            out += "-" + self.build
        return out

    def __repr__(self):
        return "Version(major={major}, minor={minor}, patch={patch}, build={build})".format(**self.segments)

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

    @property
    def prerelease(self):
        return self.build.split('.')

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
            version_str = cls.clean(version_str)
            primary, _, build = version_str.partition('-')
            parts = iter(primary.split('.'))
            vmajor = int(next(parts))
            vminor = int(next(parts, 0)) or None
            vpatch = int(next(parts, 0)) or None
            return cls(vmajor, vminor, vpatch, build)
        except ValueError as e:
            raise VersionParseException('Invalid version string {}'.format(version_str)) from e

    @staticmethod
    def clean(version_str):
        return version_str.strip().lstrip('=v')


@total_ordering
class Comparator(object):
    """
    Version Comparator: >3.0.1, <=2.1.17, etc.
    """
    def __init__(self, operator, version):
        self.operator = operator
        self.version = version

    def __str__(self):
        return self.operator + str(self.version)

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        if other.direction == self.direction:
            if self.direction < 0:
                return self.version < other.version
            else:
                return other.version < self.version
        else:
            return other.direction > self.direction

    def satisfies(self, version):
        return self.operation(version)

    def intersects(self, other):
        return self.intersection(other) is not None

    def intersection(self, other):
        intersection = None
        if self.direction == 0 and other.satisfies(self.version):
            intersection = VersionRange(self)
        elif other.direction == 0 and self.satisfies(other.version):
            intersection = VersionRange(other)
        elif (self.direction < 0 and other.direction < 0) or (self.direction >= 0 and other.direction >= 0):
            smaller, larger = sorted([self, other])
            if larger.satisfies(smaller.version):
                intersection = VersionRange(smaller)
        elif self.satisfies(other.version) and other.satisfies(self.version):
            smaller, larger = sorted([self, other], reverse=True)
            intersection = VersionRange(smaller, larger)

        print('Intersection of {} and {} is {}'.format(self, other, intersection))

        return intersection

    @property
    def operation(self):
        """
        The operation map seems backwards for less than/greater than comparisons because we are comparing
        as the right side of the equation, not the left.
        :return: {func} The appropriate comparison operation
        """
        call_map = {
            '<': self.version.__gt__,
            '<=': self.version.__ge__,
            '>': self.version.__lt__,
            '>=': self.version.__le__,
            '=': self.version.__eq__
        }
        return call_map[self.operator]

    @property
    def direction(self):
        direction_map = {
            '<': -2,
            '<=': -1,
            '=': 0,
            '>': 1,
            '>=': 2
        }
        return direction_map[self.operator]

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
    def __init__(self, lower, upper=None):
        self.lower = lower
        self.upper = upper

    def __contains__(self, item):
        if isinstance(item, str):
            item = Version.parse(item)
        return self.lower.satisfies(item) and (self.upper is None or self.upper.satisfies(item))

    def __str__(self):
        vrange = str(self.lower)
        if self.upper is not None:
            vrange += ' ' + str(self.upper)
        return vrange

    @property
    def max(self):
        max_version = None
        if self.upper is None:
            if self.lower.operator in ('=', '<='):
                max_version = self.lower.version
            elif self.lower.operator in ('>', '>='):
                max_version = ''
        elif self.upper.operator == '<=':
            max_version = self.upper.version
        return max_version

    def is_over(self, version):
        return self.upper is not None and not self.upper.satisfies(version) and self.lower.satisfies(version)

    def is_under(self, version):
        return not self.lower.satisfies(version) and self.upper.satisfies(version)

    def intersects(self, other):
        if self.upper is None and other.upper is None:
            return self.lower.intersects(other.lower)

        if self.upper is None:
            return self.lower.intersects(other.upper)

        if other.upper is None:
            return other.lower.intersects(self.upper) and other.lower.intersects()

        return self.upper.intersects(other.lower) and self.lower.intersects(other.upper)

    def intersection(self, other):
        if self.upper is None and other.upper is None:
            return self.lower.intersection(other.lower)

        if self.upper is None:
            return self.lower.intersection(other.upper)

        if other.upper is None:
            return other.lower.intersects(self.upper) and other.lower.intersects()

        return self.upper.intersects(other.lower) and self.lower.intersects(other.upper)

    @staticmethod
    def valid(v):
        pass

    @classmethod
    def intersection(cls, r1, r2):
        if r1.upper is None and r2.upper is None:
            return cls(r1.lower.intersection(r2.lower))

        if r1.upper is None:
            return r1.lower.intersection(r2.upper)

        if r2.upper is None:
            return r2.lower if r2.lower in r2 else None

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

        cl = Comparator.parse(lower)

        if cl.operator == '=':
            cu = Comparator.parse(lower)
        else:
            cu = None

        return cls(cl, cu)


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

    def intersects(self, spec):
        for r in self.ranges:
            if any(r.intersects(s) for s in spec.ranges):
                return True
        return False

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
