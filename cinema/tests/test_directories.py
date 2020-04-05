from django.test import TestCase

import os
from cinema import directories


class TestDirectories(TestCase):
    def setUp(self):
        self.seq = list(range(10))

    def tearDown(self):
        pass

    def test_base(self):
        os.path.isdir(directories.base())
        os.path.exists(directories.base("__init__.py"))

    def test_tests(self):
        os.path.isdir(directories.test())
        os.path.exists(directories.test("__init__.py"))

    def test_data(self):
        os.path.isdir(directories.test())
        os.path.exists(directories.test("README.md"))
