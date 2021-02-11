from django.test import TestCase

import numpy as np
from numpy.linalg import norm

from cinema.cinegraph.grapher import PersonNode, WorkNode
from cinema.tests import data4tests
from cinema.cinegraph import fame


class TestFame(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_normalized_exponential_decay(self):
        actual = fame.normalized_exponential_decay(4)
        expected = np.array([0.56285534, 0.26060938, 0.12066555, 0.05586973])
        self.assertAlmostEqual(0, norm(actual - expected))

    def test_get_people(self):
        g = data4tests.get_small_graph()
        people = fame.get_people(g)
        self.assertEqual(660, len(people))
        self.assertTrue(PersonNode(1669) in people)
        for p in people:
            self.assertTrue(p.is_person)

    def test_get_works(self):
        g = data4tests.get_small_graph()
        works = fame.get_works(g)
        self.assertEqual(300, len(works))
        self.assertTrue(WorkNode(119567) in works)
        for w in works:
            self.assertFalse(w.is_person)

    def test_fame_by_number_of_works(self):
        g = data4tests.get_small_graph()
        people_degree = fame.fame_by_number_of_works(g)
        self.assertEqual(660, len(people_degree))
        actual = [p for p, _ in people_degree[:4]]
        expected = [PersonNode(194), PersonNode(545), PersonNode(147), PersonNode(93)]
        self.assertEqual(expected, actual)
        actual = [d for _, d in people_degree[:4]]
        expected = [57, 56, 50, 46]
        self.assertEqual(expected, actual)

    def test_fame_by_pagerank(self):
        g = data4tests.get_small_graph()
        people_rank, _ = fame.fame_by_pagerank(g)
        actual = [p for p, _ in people_rank[:4]]
        expected = [PersonNode(545), PersonNode(194), PersonNode(147), PersonNode(93)]
        self.assertEqual(expected, actual)
        actual = [r for _, r in people_rank[:4]]
        expected = np.array(
            [
                0.02079940230132745,
                0.01956018860654516,
                0.01724945845804374,
                0.01593796482225136,
            ]
        )
        self.assertAlmostEqual(0, norm(actual - expected))

    def test_works_by_pagerank(self):
        g = data4tests.get_small_graph()
        works_rank, _ = fame.works_by_pagerank(g)
        actual = [w for w, _ in works_rank[:4]]
        expected = [
            WorkNode(3154822),
            WorkNode(118901),
            WorkNode(1233192),
            WorkNode(98638),
        ]
        self.assertEqual(expected, actual)
        actual = [r for _, r in works_rank[:4]]
        expected = np.array(
            [
                0.0033347298102977384,
                0.0019010827959628127,
                0.0019010827959628127,
                0.0019010827959628127,
            ]
        )
        self.assertAlmostEqual(0, norm(actual - expected))

    def test_neighbor_features(self):
        g = data4tests.get_small_graph()
        ia = data4tests.MockIMBD(g)
        ratings = fame.neighbor_features(
            g, PersonNode(194), lambda m: ia.get_movie(m.id)["rating"]
        )
        self.assertAlmostEqual(4.699903862142268, ratings[WorkNode(160513)])
        self.assertAlmostEqual(7.70552832501407, ratings[WorkNode(1658801)])
        self.assertEqual(57, len(ratings))

    def test_weight_by_cast_order(self):
        g = data4tests.get_small_graph()
        ia = data4tests.MockIMBD(g)
        fame.weight_by_cast_order(g, ia)
        for edge in g.edges:
            self.assertIn("weight", g.edges[edge])
        neighbors = list(g.neighbors((WorkNode(206634))))
        self.assertEqual(4, len(neighbors))
        neighbors.sort(
            key=lambda p: g.edges[(WorkNode(206634), p)]["weight"], reverse=True
        )
        actual = [g.edges[(m, WorkNode(206634))]["weight"] for m in neighbors]
        expected = fame.normalized_exponential_decay(4)
        self.assertAlmostEqual(0, norm(actual - expected))

        # order of cast should be same as order of weights from highest to lowest
        cast = ia.get_movie(206634)["cast"]
        for i, actor in enumerate(cast):
            self.assertEqual(actor.getID(), neighbors[i].id)

    def test_weight_zero(self):
        g = data4tests.get_small_graph()
        fame.weight_zero(g)
        for edge in g.edges:
            self.assertEqual(0, g.edges[edge]["weight"])

    def test_weight_by_rating(self):
        g = data4tests.get_small_graph()
        ia = data4tests.MockIMBD(g)
        fame.weight_by_feature_order(
            g,
            nodes=fame.get_people(g),
            get_feature=lambda m: ia.get_movie(m.id)["rating"],
        )

        for edge in g.edges:
            self.assertIn("weight", g.edges[edge])
        neighbors = list(g.neighbors((PersonNode(194))))
        self.assertEqual(57, len(neighbors))
        neighbors.sort(
            key=lambda m: g.edges[(PersonNode(194), m)]["weight"], reverse=True
        )
        actual = [g.edges[(PersonNode(194), m)]["weight"] for m in neighbors]
        expected = fame.normalized_exponential_decay(57)
        self.assertAlmostEqual(0, norm(actual - expected))

        # order of ratings should be same as order of weights from highest to lowest
        for i in range(56):
            self.assertTrue(
                ia.get_movie(neighbors[i].id)["rating"]
                >= ia.get_movie(neighbors[i + 1].id)["rating"]
            )

    def test_weight_by_votes(self):
        g = data4tests.get_small_graph()
        ia = data4tests.MockIMBD(g)
        fame.weight_by_feature_order(
            g,
            nodes=fame.get_people(g),
            get_feature=lambda m: ia.get_movie(m.id)["votes"],
        )

        for edge in g.edges:
            self.assertIn("weight", g.edges[edge])
        neighbors = list(g.neighbors((PersonNode(194))))
        self.assertEqual(57, len(neighbors))
        neighbors.sort(
            key=lambda m: g.edges[(PersonNode(194), m)]["weight"], reverse=True
        )
        actual = [g.edges[(PersonNode(194), m)]["weight"] for m in neighbors]
        expected = fame.normalized_exponential_decay(57)
        self.assertAlmostEqual(0, norm(actual - expected))

        # order of vote count should be same as order of weights from highest to lowest
        for i in range(56):
            self.assertTrue(
                ia.get_movie(neighbors[i].id)["votes"]
                >= ia.get_movie(neighbors[i + 1].id)["votes"]
            )
