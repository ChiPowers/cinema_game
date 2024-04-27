from django.test import TestCase

import math
import networkx as nx

from cinema.tests.fixture_imbd_tsv import FixtureIMDbTsv
from cinema.cinegraph import weights
from cinema.cinegraph import imdb_tsv
from cinema.cinegraph.node_types import PersonNode, WorkNode


class TestWeights(TestCase, FixtureIMDbTsv):
    def setUp(self):
        FixtureIMDbTsv.setUp(self)

    def tearDown(self):
        pass

    def make_multi_weight_graph(self):
        g = nx.cycle_graph(3)
        g.edges[(0, 1)].update({"a": 0, "b": 1})
        g.edges[(1, 2)].update({"a": 3, "b": 2})
        g.edges[(2, 0)].update({"a": 1, "b": -1})
        return g

    def test_order_weight(self):
        self.assertAlmostEqual(1, weights.credit_order_weight(1))
        self.assertAlmostEqual(0.4172170546520899, weights.credit_order_weight(3))
        self.assertAlmostEqual(0.12993833825732815, weights.credit_order_weight(5))
        self.assertAlmostEqual(0.004945246313269536, weights.credit_order_weight(10))

    def test_ratings_weight(self):
        self.assertEqual(1, weights.rating_weight(10))
        self.assertEqual(0.75, weights.rating_weight(7.5))
        self.assertEqual(0.25, weights.rating_weight(2.5))

    def test_normalized_activation(self):
        self.assertAlmostEqual(0.01798620996209155, weights.normalized_activation(-2))
        self.assertAlmostEqual(0.11920292202211757, weights.normalized_activation(-1))
        self.assertAlmostEqual(0.5, weights.normalized_activation(0))
        self.assertAlmostEqual(0.8807970779778824, weights.normalized_activation(1))
        self.assertAlmostEqual(0.9820137900379085, weights.normalized_activation(2))

    def test_mean_std(self):
        g = self.make_graph()
        mu, sigma = weights.node_mean_std(
            g, imdb_tsv.get_votes, lambda n, _: not n.is_person
        )
        self.assertAlmostEqual(13005.75, mu)
        self.assertAlmostEqual(8347.634017342878, sigma)

    def test_votes_mean_std(self):
        g = self.make_graph()
        mu, sigma = weights.votes_mean_std(g)
        self.assertAlmostEqual(13005.75, mu)
        self.assertAlmostEqual(8347.634017342878, sigma)

    def test_product_of_weights(self):
        g = self.make_multi_weight_graph()
        new_weight = weights.multiply_weights(g, "a", "b")
        self.assertEqual("a_b", new_weight)
        self.assertEqual(0, g.edges[(0, 1)]["a_b"])
        self.assertEqual(6, g.edges[(1, 2)]["a_b"])
        self.assertEqual(-1, g.edges[(2, 0)]["a_b"])

    def test_sum_of_weights(self):
        g = self.make_multi_weight_graph()
        new_weight = weights.sum_weights(g, "a", "b")
        self.assertEqual("a_b", new_weight)
        self.assertEqual(1, g.edges[(0, 1)]["a_b"])
        self.assertEqual(5, g.edges[(1, 2)]["a_b"])
        self.assertEqual(0, g.edges[(2, 0)]["a_b"])

    def test_normalize_votes_weights(self):
        def activate(x):
            y = (x - mu) / sigma
            y = (math.tanh(y) + 1) / 2
            return y

        g = self.make_graph()
        weight = "vote_weight"
        mu, sigma = 13005.75, 8347.634017342878
        weights.weight_by_normalized_votes(g, weight=weight)
        self.assertAlmostEqual(
            activate(1497), g.edges[(PersonNode(1), WorkNode(43044))][weight]
        )
        self.assertAlmostEqual(
            activate(24896), g.edges[(PersonNode(1), WorkNode(50419))][weight]
        )
        self.assertAlmostEqual(
            activate(14369), g.edges[(PersonNode(2), WorkNode(117057))][weight]
        )
        self.assertAlmostEqual(
            activate(1497), g.edges[(PersonNode(861703), WorkNode(43044))][weight]
        )

    def test_actors_only_weights(self):
        g = self.make_graph()
        weight = "actor_weight"
        weights.weight_only_actors(g, weight=weight)
        self.assertEqual(1, g.edges[(PersonNode(1), WorkNode(43044))][weight])
        self.assertEqual(1, g.edges[(PersonNode(1), WorkNode(50419))][weight])
        self.assertEqual(1, g.edges[(PersonNode(2), WorkNode(117057))][weight])
        self.assertEqual(0, g.edges[(PersonNode(861703), WorkNode(43044))][weight])

    def test_credit_order_weights(self):
        def activation(x):
            y = (1 - x) / 3
            return math.tanh(y) + 1

        g = self.make_graph()
        weight = "credit_weight"
        weights.weight_credit_order(g, weight=weight)
        self.assertEqual(
            activation(1), g.edges[(PersonNode(1), WorkNode(43044))][weight]
        )
        self.assertEqual(
            activation(2), g.edges[(PersonNode(1), WorkNode(50419))][weight]
        )
        self.assertEqual(
            activation(3), g.edges[(PersonNode(2), WorkNode(117057))][weight]
        )
        self.assertEqual(
            activation(5), g.edges[(PersonNode(861703), WorkNode(43044))][weight]
        )

    def test_rating_weights(self):
        g = self.make_graph()
        weight = "rating_weight"
        weights.weight_by_rating(g, weight=weight)
        self.assertAlmostEqual(0.69, g.edges[(PersonNode(1), WorkNode(43044))][weight])
        self.assertAlmostEqual(0.70, g.edges[(PersonNode(1), WorkNode(50419))][weight])
        self.assertAlmostEqual(0.66, g.edges[(PersonNode(2), WorkNode(117057))][weight])
        self.assertAlmostEqual(
            0.69, g.edges[(PersonNode(861703), WorkNode(43044))][weight]
        )

    def test_missing_weights(self):
        g = self.make_graph()
        del g.nodes[WorkNode(43044)]["rating"]
        weight = "rating_weight"
        weights.weight_by_rating(g, weight=weight)
        self.assertAlmostEqual(0, g.edges[(PersonNode(1), WorkNode(43044))][weight])
        self.assertAlmostEqual(0.70, g.edges[(PersonNode(1), WorkNode(50419))][weight])
        self.assertAlmostEqual(0.66, g.edges[(PersonNode(2), WorkNode(117057))][weight])
        self.assertAlmostEqual(
            0, g.edges[(PersonNode(861703), WorkNode(43044))][weight]
        )
