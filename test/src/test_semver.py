import unittest
from src import semver


class TestSemver(unittest.TestCase):
    def test_range_max(self):
        winner = semver.range_max('1.*', ['1.0.9', '2.56.7', '1.19', '1.4.8'])
        self.assertEqual(winner, semver.Version(1, 19, 0))

    def test_range_min(self):
        winner = semver.range_min('1.*', ['1.0.9', '2.56.7', '1.19', '1.4.8'])
        self.assertEqual(winner, semver.Version(1, 0, 9))


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

    def test_cmp(self):
        v1 = semver.Version.parse('1.2.3')
        v2 = semver.Version.parse('1.2.4')
        self.assertTrue(v1 < v2)

        v1 = semver.Version.parse('1.2.3')
        v2 = semver.Version.parse('1.2.4')
        self.assertTrue(v1 <= v2)

        v1 = semver.Version.parse('1.13.3')
        v2 = semver.Version.parse('1.2.4')
        self.assertTrue(v1 > v2)

        v1 = semver.Version.parse('1.3.3')
        v2 = semver.Version.parse('1.2.4')
        self.assertTrue(v1 != v2)

        v1 = semver.Version.parse('1.2.3-alpha')
        v2 = semver.Version.parse('1.2.3-beta')
        self.assertTrue(v1 < v2)

        v1 = semver.Version.parse('1.2.3-alpha.0')
        v2 = semver.Version.parse('1.2.3-alpha.1')
        self.assertTrue(v1 < v2)


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

    def test_satisfies(self):
        c = semver.Comparator('=', semver.Version(1, 2, 3))
        self.assertTrue(c.satisfies(semver.Version(1, 2, 3)))

        c = semver.Comparator('<', semver.Version(1, 2, 3))
        self.assertTrue(c.satisfies(semver.Version(1, 1, 3)))

        c = semver.Comparator('>', semver.Version(1, 2, 3))
        self.assertTrue(c.satisfies(semver.Version(1, 3, 3)))

        c = semver.Comparator.parse('>1.0.0')
        self.assertFalse(c.satisfies(semver.Version(1, 0, 0)))

    def test_intersects(self):
        c1 = semver.Comparator.parse('<=1.2.3')
        c2 = semver.Comparator.parse('<=2.3.4')
        self.assertTrue(c1.intersects(c2))

        c1 = semver.Comparator.parse('<=1.2.3')
        c2 = semver.Comparator.parse('>2.3.4')
        self.assertFalse(c1.intersects(c2))

        c1 = semver.Comparator.parse('=1.2.3')
        c2 = semver.Comparator.parse('>1.0.0')
        self.assertTrue(c1.intersects(c2))

        c1 = semver.Comparator.parse('=1.0.0')
        c2 = semver.Comparator.parse('<1.0.0')
        self.assertFalse(c1.intersects(c2))

        c1 = semver.Comparator.parse('>1.0.0')
        c2 = semver.Comparator.parse('<1.0.0')
        self.assertFalse(c1.intersects(c2))

        c1 = semver.Comparator.parse('>1.0.0')
        c2 = semver.Comparator.parse('<1.1.0')
        self.assertTrue(c1.intersects(c2))

        c1 = semver.Comparator.parse('>=4.2.3')
        c2 = semver.Comparator.parse('<3.4.5')
        self.assertFalse(c1.intersects(c2))


class TestVersionRange(unittest.TestCase):
    def test_parse(self):
        r = semver.VersionRange.parse('>=1.2.3')
        self.assertIsInstance(r, semver.VersionRange)
        self.assertEqual(r.lower.operator, '>=')
        self.assertEqual(r.lower.version, semver.Version(1, 2, 3))
        self.assertIsNone(r.upper)

        r = semver.VersionRange.parse('1.2.3 - 4.5.6')
        self.assertIsInstance(r, semver.HyphenRange)

        r = semver.VersionRange.parse('1.2.x')
        self.assertIsInstance(r, semver.XRange)

        r = semver.VersionRange.parse('~1.2.3')
        self.assertIsInstance(r, semver.TildeRange)

        r = semver.VersionRange.parse('^1.2.3')
        self.assertIsInstance(r, semver.CaretRange)

    def test_contains(self):
        r = semver.VersionRange.parse('1.2.3 - 4.5.6')
        self.assertTrue(semver.Version(2, 3, 4) in r)

        r = semver.VersionRange.parse('1.2.x')
        self.assertTrue('1.2.3' in r)

        r = semver.VersionRange.parse('^1.2.0')
        self.assertTrue('1.3.4' in r)

        r = semver.VersionRange.parse('~1.2')
        self.assertTrue('1.2.567' in r)

        r = semver.VersionRange.parse('*')
        self.assertTrue('1.1.1' in r)

    def test_cmp(self):
        r = semver.VersionRange.parse('1.2.3 - 4.5.6')
        self.assertTrue(r.is_over(semver.Version(5, 0, 0)))
        self.assertFalse(r.is_over(semver.Version(3, 0, 0)))
        self.assertFalse(r.is_over(semver.Version(1, 1, 0)))

        r = semver.VersionRange.parse('1.2.3 - 4.5.6')
        self.assertFalse(r.is_under(semver.Version(5, 0, 0)))
        self.assertFalse(r.is_under(semver.Version(3, 0, 0)))
        self.assertTrue(r.is_under(semver.Version(1, 1, 0)))

    def test_intersects(self):
        r1 = semver.VersionRange.parse('1.2.3 - 2.3.4')
        r2 = semver.VersionRange.parse('2.1.0 - 3.4.5')
        self.assertTrue(r1.intersects(r2))

        r1 = semver.VersionRange.parse('>=1.2.3')
        r2 = semver.VersionRange.parse('2.1.0 - 3.4.5')
        self.assertTrue(r1.intersects(r2))

        r1 = semver.VersionRange.parse('>=4.2.3')
        r2 = semver.VersionRange.parse('2.1.0 - 3.4.5')
        self.assertFalse(r1.intersects(r2))


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
