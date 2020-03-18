from django.test import TestCase

import numpy as np
import networkx as nx

from cinema.tests.data4tests import get_small_graph
from cinema.cinegraph.grapher import PersonNode
from cinema.cinegame import game_maker


class TestGameMaker(TestCase):
    def setUp(self):
        self.g = get_small_graph()
        self.r = np.random.RandomState(42)

    def tearDown(self):
        pass

    def test_make_game_by_iteration(self):
        # select one third of the actors in the graph as candidates for start and end nodes
        candidates = [node for node in self.g.nodes if node.is_person and (node.id % 3 == 0)]

        # choose actors who have been in the same movie
        a, b = game_maker.make_game_by_iteration(self.g, candidates, 1, r=self.r)
        self.assertEqual(PersonNode(51), a)
        self.assertEqual(PersonNode(532290), b)
        self.assertEqual(2, nx.shortest_path_length(self.g, a, b))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 1, r=self.r)
        self.assertEqual(PersonNode(1512), a)
        self.assertEqual(PersonNode(147), b)
        self.assertEqual(2, nx.shortest_path_length(self.g, a, b))

        # choose actors who are two movies apart
        a, b = game_maker.make_game_by_iteration(self.g, candidates, 2, r=self.r)
        self.assertEqual(PersonNode(171513), a)
        self.assertEqual(PersonNode(1644), b)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 2, r=self.r)
        self.assertEqual(PersonNode(378), a)
        self.assertEqual(PersonNode(1512), b)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 2, r=self.r)
        self.assertEqual(PersonNode(770961), a)
        self.assertEqual(PersonNode(138), b)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))

        # choose some actors that are three movies apart
        a, b = game_maker.make_game_by_iteration(self.g, candidates, 3, r=self.r)
        self.assertEqual(PersonNode(330687), a)
        self.assertEqual(PersonNode(1605114), b)
        self.assertEqual(6, nx.shortest_path_length(self.g, a, b))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 3, r=self.r)
        self.assertEqual(PersonNode(123), a)
        self.assertEqual(PersonNode(861915), b)
        self.assertEqual(6, nx.shortest_path_length(self.g, a, b))
