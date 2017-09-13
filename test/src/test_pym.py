import unittest
from src import pym


class TestPymApp(unittest.TestCase):

    def setUp(self):
        self.app = pym.PymApp(None)

    def test_pass(self):
        self.assertEqual(3, 3)
