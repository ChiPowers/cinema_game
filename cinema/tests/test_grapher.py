import networkx as nx
from cinema.cinegraph import grapher

from django.test import TestCase


class TestGrapher(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_arc(self):
        g = nx.Graph()
        grapher.add_arc(g, "The Air I Breathe", "Kevin Bacon", job='actor')
        grapher.add_arc(g, "The Air I Breathe", "Sarah Michelle Geller", job='actress')
        grapher.add_arc(g, "A Powerful Noise Live", "Sarah Michelle Geller", job='self')
        grapher.add_arc(g, "A Powerful Noise Live", "Natalie Portman", job='self')

        self.assertEqual(5, g.number_of_nodes())
        self.assertEqual(4, g.number_of_edges())

        self.assertEqual('movie', g.nodes["The Air I Breathe"]['t'])
        self.assertEqual('movie', g.nodes["A Powerful Noise Live"]['t'])

        self.assertEqual('person', g.nodes["Kevin Bacon"]['t'])
        self.assertEqual('person', g.nodes["Sarah Michelle Geller"]['t'])
        self.assertEqual('person', g.nodes["Natalie Portman"]['t'])

        self.assertEqual({'actor'}, g.edges[("The Air I Breathe", "Kevin Bacon")]['job'])
        self.assertEqual({'actress'}, g.edges[("The Air I Breathe", "Sarah Michelle Geller")]['job'])
        self.assertEqual({'self'}, g.edges[("A Powerful Noise Live", "Sarah Michelle Geller")]['job'])
        self.assertEqual({'self'}, g.edges[("A Powerful Noise Live", "Natalie Portman")]['job'])
