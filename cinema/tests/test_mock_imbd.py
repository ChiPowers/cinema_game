from django.test import TestCase

import numpy as np
from numpy.linalg import norm

from cinema.cinegraph.grapher import PersonNode, WorkNode
from cinema.tests import data4tests


class TestFame(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_mock_actor(self):
        one = data4tests.MockImdbObject.mock_actor(PersonNode(1))
        self.assertEqual(1, one.getID())
        self.assertEqual("1", one['name'])
        self.assertAlmostEqual(41.7022004702574, one['pay'])

    def test_mock_movie(self):
        one = data4tests.MockImdbObject.mock_movie(WorkNode(1))
        self.assertEqual(1, one.getID())
        self.assertEqual('1', one['title'])
        self.assertEqual(38, one['votes'])
        self.assertAlmostEqual(9.971848109388686, one['rating'])

    def test_mock_imdb(self):
        g = data4tests.get_small_graph()
        ia = data4tests.MockIMBD(g)
        person_node = PersonNode(194)
        p = ia.get_person(194)
        self.assertEqual('194', p['name'])
        expected = ['172396', '117791', '427968', '206634']
        actual = [m['title'] for m in p['known for']]
        self.assertEqual(expected, actual)
        expected = [59, 711, 81, 140]
        actual = [m['votes'] for m in p['known for']]
        self.assertEqual(expected, actual)
        # notice that expected rating decreases with movie in known for
        expected = np.array([9.705718793008499, 9.63631897055048, 9.10501141396861, 8.987711839835399])
        actual = [m['rating'] for m in p['known for']]
        self.assertAlmostEqual(0, norm(expected - actual))
