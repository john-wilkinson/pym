import unittest
from src import semver


class TestVersion(unittest.TestCase):
    def test_parse(self):
        v = semver.Version.parse('1.2.3')
        self.assertEqual(v, semver.Version(1, 2, 3))

        v = semver.Version.parse('1.2.3-abc')
        self.assertEqual(v, semver.Version(1, 2, 3, 'abc'))

        v = semver.Version.parse('1.2.3-4.5.6')
        self.assertEqual(v, semver.Version(1, 2, 3, '4.5.6'))

        v = semver.Version.parse('v1.2.3')
        self.assertEqual(v, semver.Version(1, 2, 3))

        v = semver.Version.parse('=1.2.3')
        self.assertEqual(v, semver.Version(1, 2, 3))

        v = semver.Version.parse('=1.2')
        self.assertEqual(v, semver.Version(1, 2, 0))
        self.assertTrue(v.partial)

        v = semver.Version.parse('=1')
        self.assertEqual(v, semver.Version(1, 0, 0))
        self.assertTrue(v.partial)

    def test_inc(self):
        v = semver.Version.parse('1.2.3')
        v.inc('minor')
        self.assertEqual(v, semver.Version(1, 3, 0))


class TestComparator(unittest.TestCase):
    def test_parse(self):
        c = semver.Comparator.parse('<1.2.3')
        self.assertEqual(c.operator, '<')
        self.assertEqual(c.version, semver.Version(1, 2, 3))

        c = semver.Comparator.parse('>=1.2.3')
        self.assertEqual(c.operator, '>=')
        self.assertEqual(c.version, semver.Version(1, 2, 3))

        c = semver.Comparator.parse('1.2.3')
        self.assertEqual(c.operator, '=')
        self.assertEqual(c.version, semver.Version(1, 2, 3))


class TestVersionRange(unittest.TestCase):
    def test_parse(self):
        r = semver.VersionRange.parse('1.2.3 - 4.5.6')
        self.assertIsInstance(r, semver.HyphenRange)

        r = semver.VersionRange.parse('1.2.x')
        self.assertIsInstance(r, semver.XRange)

        r = semver.VersionRange.parse('~1.2.3')
        self.assertIsInstance(r, semver.TildeRange)

        r = semver.VersionRange.parse('^1.2.3')
        self.assertIsInstance(r, semver.CaretRange)


class TestHyphenRange(unittest.TestCase):
    def test_parse(self):
        r = semver.HyphenRange.parse('1.2.3 - 4.5.6')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 2, 3))
        self.assertEqual(r.upper.operator, '<=')
        self.assertEqual(r.upper.version, semver.Version(4, 5, 6))

        r = semver.HyphenRange.parse('1.2.3 - 4.5')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 2, 3))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(4, 5, 0))


class TestXRange(unittest.TestCase):
    def test_parse(self):
        r = semver.XRange.parse('1.2.x')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 2, 0))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(1, 3, 0))

        r = semver.XRange.parse('1.X')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 0, 0))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(2, 0, 0))

        r = semver.XRange.parse('*')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(0, 0, 0))
        self.assertIsNone(r.upper)


class TestTildeRange(unittest.TestCase):
    def test_parse(self):
        r = semver.TildeRange.parse('~1.2.3')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 2, 3))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(1, 3, 0))


class TestCaretRange(unittest.TestCase):
    def test_parse(self):
        r = semver.CaretRange.parse('^1.2.3')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 2, 3))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(2, 0, 0))

        r = semver.CaretRange.parse('^0.2.3')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(0, 2, 3))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(0, 3, 0))

        r = semver.CaretRange.parse('^0.0.3')
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(0, 0, 3))
        self.assertEqual(r.upper.operator, '<')
        self.assertEqual(r.upper.version, semver.Version(0, 0, 4))
