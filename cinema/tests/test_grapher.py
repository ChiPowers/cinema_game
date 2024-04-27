import networkx as nx
from cinema.cinegraph import grapher
from cinema.cinegraph.node_types import ProfessionalNode, PersonNode, WorkNode

from django.test import TestCase


class TestGrapher(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_arc(self):
        g = nx.Graph()
        grapher.add_arc(g, "The Air I Breathe", "Kevin Bacon", job="actor")
        grapher.add_arc(g, "The Air I Breathe", "Sarah Michelle Geller", job="actress")
        grapher.add_arc(g, "A Powerful Noise Live", "Sarah Michelle Geller", job="self")
        grapher.add_arc(g, "A Powerful Noise Live", "Natalie Portman", job="self")

        self.assertEqual(5, g.number_of_nodes())
        self.assertEqual(4, g.number_of_edges())

        self.assertIn(WorkNode("The Air I Breathe"), g.nodes)
        self.assertIn(WorkNode("A Powerful Noise Live"), g.nodes)

        self.assertIn(PersonNode("Kevin Bacon"), g.nodes)
        self.assertIn(PersonNode("Sarah Michelle Geller"), g.nodes)
        self.assertIn(PersonNode("Natalie Portman"), g.nodes)

        self.assertEqual(
            {"actor"},
            g.edges[(WorkNode("The Air I Breathe"), PersonNode("Kevin Bacon"))]["job"],
        )
        self.assertEqual(
            {"actress"},
            g.edges[
                (WorkNode("The Air I Breathe"), PersonNode("Sarah Michelle Geller"))
            ]["job"],
        )
        self.assertEqual(
            {"self"},
            g.edges[
                (
                    WorkNode("A Powerful Noise Live"),
                    PersonNode("Sarah Michelle Geller"),
                )
            ]["job"],
        )
        self.assertEqual(
            {"self"},
            g.edges[(WorkNode("A Powerful Noise Live"), PersonNode("Natalie Portman"))][
                "job"
            ],
        )

    def test_professional_node_in_graph(self):
        # IMDB ids are integers. There are movies and people which have the same id.
        # We need node objects which can be either movies or people and which are distinct even having the same
        # integer id.

        g = nx.Graph()
        n0 = ProfessionalNode(42, True)
        n1 = ProfessionalNode(42, False)
        n2 = ProfessionalNode(48, False)

        m0 = ProfessionalNode(42, True)
        m1 = ProfessionalNode(42, False)
        m2 = ProfessionalNode(48, False)
        m3 = ProfessionalNode(0, True)

        g.add_node(n0)
        g.add_node(n1)
        g.add_node(n2)

        self.assertIn(n0, g.nodes)
        self.assertIn(n1, g.nodes)
        self.assertIn(n2, g.nodes)

        self.assertIn(m0, g.nodes)
        self.assertIn(m1, g.nodes)
        self.assertIn(m2, g.nodes)
        self.assertNotIn(m3, g.nodes)
