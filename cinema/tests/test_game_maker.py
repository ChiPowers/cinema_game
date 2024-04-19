from django.test import TestCase

import numpy as np
import networkx as nx

from .data4tests import get_small_graph
from ..cinegame import game_maker
from ..cinegraph.node_types import PersonNode


class TestGameMaker(TestCase):
    def setUp(self):
        self.g = get_small_graph()
        self.r = np.random.RandomState(42)

        # select one third of the actors in the graph as candidates for start and end nodes
        self.candidates = [
            node for node in self.g.nodes if node.is_person and (node.id % 3 == 0)
        ]

    def tearDown(self):
        pass

    def test_select_random_nodes(self):
        nodes = [PersonNode(0), PersonNode(1), PersonNode("asdf"), PersonNode("42"), PersonNode(42)]
        r = np.random.RandomState(42)

        a, = game_maker.select_random_nodes(nodes, r=r)
        self.assertEqual(PersonNode("asdf"), a)

        a, = game_maker.select_random_nodes(nodes, r=r)
        self.assertEqual(PersonNode(1), a)

        a, = game_maker.select_random_nodes(nodes, r=r)
        self.assertEqual(PersonNode("asdf"), a)

        a, b = game_maker.select_random_nodes(nodes, size=2, r=r)
        self.assertEqual(PersonNode("42"), a)
        self.assertEqual(PersonNode("asdf"), b)

        a, b = game_maker.select_random_nodes(nodes, size=2, r=r)
        self.assertEqual(PersonNode("42"), a)
        self.assertEqual(PersonNode(0), b)

        r0 = np.random.RandomState(42)
        r1 = np.random.RandomState(42)

        # selection should be repeatable of order of nodes
        for _ in range(100):
            a, b = game_maker.select_random_nodes(nodes, size=2, r=r0)
            c, d = game_maker.select_random_nodes(nodes, size=2, r=r1)
            self.assertEqual(a, c)
            self.assertEqual(b, d)

        shuffled_nodes = nodes.copy()
        r.shuffle(shuffled_nodes)

        # selection should be independent of order of nodes
        for _ in range(100):
            a, b = game_maker.select_random_nodes(nodes, size=2, r=r0)
            c, d = game_maker.select_random_nodes(shuffled_nodes, size=2, r=r1)
            self.assertEqual(a, c)
            self.assertEqual(b, d)

        # selection should be independent of type of iterable
        for _ in range(100):
            a, b = game_maker.select_random_nodes(nodes, size=2, r=r0)
            c, d = game_maker.select_random_nodes(set(nodes), size=2, r=r1)
            self.assertEqual(a, c)
            self.assertEqual(b, d)

    def test_make_people_subgraph(self):
        people_subgraph = game_maker.make_people_subgraph(self.g, self.candidates)

        candidates = set(self.candidates)

        all_subgraph_nodes = set(people_subgraph.nodes)
        self.assertTrue(candidates.issubset(all_subgraph_nodes))

        for node in people_subgraph.nodes:
            if node.is_person:
                self.assertTrue(node in candidates)
            else:
                self.assertTrue(people_subgraph.degree(node) > 0)

    def test_make_game_from_starting_node_fail(self):
        # there is no game of length five starting from the first candidate
        with self.assertRaises(game_maker.CandidateNotFoundException):
            game_maker.make_game_from_starting_node(self.g, self.candidates[0], self.candidates, 5, r=self.r)

    def test_make_game_from_starting_node(self):
        candidates = self.candidates
        # find games of length 1
        a, b = game_maker.make_game_from_starting_node(self.g, candidates[0], candidates, 1, r=self.r)
        self.assertEqual(candidates[0], a)
        self.assertEqual(2, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(PersonNode(92184), a)
        self.assertEqual(PersonNode(2091), b)

        a, b = game_maker.make_game_from_starting_node(self.g, candidates[2], candidates, 1, r=self.r)
        self.assertEqual(candidates[2], a)
        self.assertEqual(2, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(PersonNode(345), a)
        self.assertEqual(PersonNode(114), b)

        # find game of length 2
        a, b = game_maker.make_game_from_starting_node(self.g, candidates[2], candidates, 2, r=self.r)
        self.assertEqual(candidates[2], a)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(PersonNode(345), a)
        self.assertEqual(PersonNode(246), b)

        # find game of length 4
        a, b = game_maker.make_game_from_starting_node(self.g, candidates[2], candidates, 4, r=self.r)
        self.assertEqual(candidates[2], a)
        self.assertEqual(8, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(PersonNode(345), a)
        self.assertEqual(PersonNode(4851), b)

    def test_make_game_by_iteration_fail(self):
        # there is no game of length five
        with self.assertRaises(game_maker.GameNotFoundException):
            game_maker.make_game_by_iteration(self.g, self.candidates, 5, r=self.r, max_iter=10)

    def test_make_game_by_iteration(self):
        candidates = self.candidates

        # choose actors who have been in the same movie
        a, b = game_maker.make_game_by_iteration(self.g, candidates, 1, r=self.r)
        first_choice = a.id
        self.assertEqual(2, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(a, PersonNode(7955301))
        self.assertEqual(b, PersonNode(147))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 1, r=self.r)
        self.assertNotEquals(first_choice, a.id)
        self.assertEqual(2, nx.shortest_path_length(self.g, a, b))

        # choose actors who are two movies apart
        a, b = game_maker.make_game_by_iteration(self.g, candidates, 2, r=self.r)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(PersonNode(111), a)
        self.assertEqual(PersonNode(309693), b)

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 2, r=self.r)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 2, r=self.r)
        self.assertEqual(4, nx.shortest_path_length(self.g, a, b))

        # choose some actors that are three movies apart
        a, b = game_maker.make_game_by_iteration(self.g, candidates, 3, r=self.r)
        self.assertEqual(6, nx.shortest_path_length(self.g, a, b))

        a, b = game_maker.make_game_by_iteration(self.g, candidates, 3, r=self.r)
        self.assertEqual(6, nx.shortest_path_length(self.g, a, b))
        self.assertEqual(PersonNode(1605114), a)
        self.assertEqual(PersonNode(261), b)


    def test_game_maker(self):
        gm = game_maker.GameMaker(self.g, self.candidates)
        self.assertEqual(set(self.candidates), gm.candidates)

        # find games of length 1
        a, b = gm.make_game(1, r=self.r)
        self.assertEqual(2, nx.shortest_path_length(gm.g, a, b))
        self.assertEqual(PersonNode(228), a)
        self.assertEqual(PersonNode(396558), b)

        a, b = gm.make_game(2, r=self.r)
        self.assertEqual(4, nx.shortest_path_length(gm.g, a, b))
        self.assertEqual(PersonNode(168), a)
        self.assertEqual(PersonNode(102), b)

        a, b = gm.make_game(4, r=self.r)
        self.assertEqual(8, nx.shortest_path_length(gm.g, a, b))
        self.assertEqual(PersonNode(744834), a)
        self.assertEqual(PersonNode(7955301), b)

        with self.assertRaises(game_maker.GameNotFoundException):
            gm.make_game(10, r=self.r)
