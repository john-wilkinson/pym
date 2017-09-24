import unittest
from src import semver


class TestVersion(unittest.TestCase):
    def test_parse(self):
        v = semver.Version.parse('1.2.3')
        self.assertEqual(v.major, '1')
        self.assertEqual(v.minor, '2')
        self.assertEqual(v.patch, '3')
        self.assertEqual(v.build, '')

        v = semver.Version.parse('1.2.3-abc')
        self.assertEqual(v.major, '1')
        self.assertEqual(v.minor, '2')
        self.assertEqual(v.patch, '3')
        self.assertEqual(v.build, 'abc')

        v = semver.Version.parse('1.2.3-4.5.6')
        self.assertEqual(v.major, '1')
        self.assertEqual(v.minor, '2')
        self.assertEqual(v.patch, '3')
        self.assertEqual(v.build, '4.5.6')

    def test_specificity(self):
        v = semver.Version.parse('1.2.3-4.5.6')
        self.assertEqual(v.specificity, 3335)

        v = semver.Version.parse('*.^2.3-abc')
        self.assertEqual(v.specificity, 1235)

        v = semver.Version.parse('1.*.*-4.5.6')
        self.assertEqual(v.specificity, 3115)


class TestSpec(unittest.TestCase):

    def test_parse(self):
        spec = semver.Spec.parse('1.2.3 or 1.2.5-abcd')
        self.assertEqual(len(spec.versions), 2)

        v1 = spec.versions[0]
        self.assertEqual(v1.major, '1')
        self.assertEqual(v1.minor, '2')
        self.assertEqual(v1.patch, '3')
        self.assertEqual(v1.build, '')

        v2 = spec.versions[1]
        self.assertEqual(v2.major, '1')
        self.assertEqual(v2.minor, '2')
        self.assertEqual(v2.patch, '5')
        self.assertEqual(v2.build, 'abcd')

    def test_equal(self):
        self.assertTrue(semver.Spec.parse('1.2.3') == semver.Spec.parse('1.2.3'))
        self.assertFalse(semver.Spec.parse('1.2.3') == semver.Spec.parse('1.2.4'))

    def test_intersection(self):
        s1 = semver.Spec.parse('1.2.3')
        self.assertEqual(s1.intersection('1.2.3'), semver.Spec.parse('1.2.3'))
        self.assertEqual(s1.intersection('1.2.4'), semver.Spec([]))

        self.assertEqual(s1.intersection('1.2.*'), semver.Spec.parse('1.2.3'))
