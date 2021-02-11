from django.test import TestCase

import networkx as nx

from cinema.tests.fixture_imbd_tsv import FixtureIMDbTsv
from cinema.cinegraph.grapher import PersonNode, WorkNode
from cinema.cinegraph import imdb_tsv


class TestIMDbTsv(TestCase, FixtureIMDbTsv):
    def setUp(self):
        FixtureIMDbTsv.setUp(self)

    def tearDown(self):
        pass

    def test_person_node(self):
        fred = imdb_tsv.IMDbPersonNode("nm0000001")
        self.assertEqual(1, fred.id)
        self.assertTrue(fred.is_person)

    def test_work_node(self):
        three_little_words = imdb_tsv.IMDbWorkNode("tt0043044")
        self.assertEqual(43044, three_little_words.id)
        self.assertFalse(three_little_words.is_person)

    def test_add_person(self):
        g = nx.Graph()
        imdb_tsv.add_person(g, self.names[0])
        expected = {
            "name": "Fred Astaire",
            "birth": "1899",
            "death": "1987",
            "professions": {"miscellaneous", "actor", "soundtrack"},
            "known": {
                WorkNode(53137),
                WorkNode(50419),
                WorkNode(72308),
                WorkNode(43044),
            },
        }
        actual = g.nodes[PersonNode(1)]
        self.assertEqual(expected, actual)

    def test_add_work(self):
        g = nx.Graph()
        imdb_tsv.add_work(g, self.basics[0])
        expected = {
            "title": "Three Little Words",
            "adult": 0,
            "start": "1950",
            "end": "\\N",
            "runtime": "102",
            "genres": {"Biography", "Musical", "Comedy"},
        }
        actual = g.nodes[WorkNode(43044)]
        self.assertEqual(expected, actual)

    def test_update_rating(self):
        g = nx.Graph()
        imdb_tsv.add_work(g, self.basics[0])
        imdb_tsv.update_rating(g, self.ratings[0])
        expected = {
            "title": "Three Little Words",
            "adult": 0,
            "start": "1950",
            "end": "\\N",
            "runtime": "102",
            "genres": {"Musical", "Comedy", "Biography"},
            "rating": 6.9,
            "votes": 1497,
        }
        actual = g.nodes[WorkNode(43044)]
        self.assertEqual(expected, actual)

    def test_add_contribution(self):
        g = self.make_graph()
        expected = {"ordering": 1, "contributions": {"actor": {"job": "\\N"}}}
        actual = g.edges[(PersonNode(1), WorkNode(43044))]
        self.assertEqual(expected, actual)

    def test_has_profession(self):
        g = self.make_graph()
        self.assertFalse(
            imdb_tsv.has_profession_in_graph(g, PersonNode(8888888888), "actor")
        )
        self.assertFalse(imdb_tsv.has_profession_in_graph(g, PersonNode(1), "producer"))
        self.assertTrue(imdb_tsv.has_profession_in_graph(g, PersonNode(3), "producer"))

    def test_is_actor(self):
        g = self.make_graph()
        self.assertTrue(imdb_tsv.is_actor_in_graph(g, PersonNode(1)))
        self.assertFalse(imdb_tsv.is_actor_in_graph(g, PersonNode(2)))
        self.assertFalse(imdb_tsv.is_actor_in_graph(g, PersonNode(3)))

    def test_is_actress(self):
        g = self.make_graph()
        self.assertFalse(imdb_tsv.is_actress_in_graph(g, PersonNode(1)))
        self.assertTrue(imdb_tsv.is_actress_in_graph(g, PersonNode(2)))
        self.assertTrue(imdb_tsv.is_actress_in_graph(g, PersonNode(3)))

    def test_contributed_as(self):
        g = self.make_graph()
        thorpe = PersonNode(861703)
        three_little_words = WorkNode(43044)
        the_mirror_has_two_faces = WorkNode(117057)
        self.assertIn(three_little_words, g.nodes)
        self.assertIn((thorpe, three_little_words), g.edges)
        self.assertTrue(
            imdb_tsv.contributed_as_in_graph(g, thorpe, three_little_words, "director")
        )
        self.assertFalse(
            imdb_tsv.contributed_as_in_graph(g, thorpe, three_little_words, "cook")
        )
        self.assertFalse(
            imdb_tsv.contributed_as_in_graph(
                g, thorpe, the_mirror_has_two_faces, "director"
            )
        )

    def test_acted_in(self):
        g = self.make_graph()
        thorpe = PersonNode(861703)
        astaire = PersonNode(1)
        bacall = PersonNode(2)
        three_little_words = WorkNode(43044)
        the_mirror_has_two_faces = WorkNode(117057)
        self.assertFalse(imdb_tsv.acted_in_in_graph(g, thorpe, three_little_words))
        self.assertFalse(
            imdb_tsv.acted_in_in_graph(g, thorpe, the_mirror_has_two_faces)
        )
        self.assertTrue(imdb_tsv.acted_in_in_graph(g, astaire, three_little_words))
        self.assertFalse(
            imdb_tsv.acted_in_in_graph(g, astaire, the_mirror_has_two_faces)
        )
        self.assertFalse(imdb_tsv.acted_in_in_graph(g, bacall, three_little_words))
        self.assertTrue(imdb_tsv.acted_in_in_graph(g, bacall, the_mirror_has_two_faces))

    def test_votes(self):
        g = self.make_graph()
        three_little_words = g.nodes[WorkNode(43044)]
        the_mirror_has_two_faces = g.nodes[WorkNode(117057)]
        self.assertEqual(1497, imdb_tsv.get_votes(three_little_words))
        self.assertEqual(14369, imdb_tsv.get_votes(the_mirror_has_two_faces))

    def test_rating(self):
        g = self.make_graph()
        three_little_words = g.nodes[WorkNode(43044)]
        the_mirror_has_two_faces = g.nodes[WorkNode(117057)]
        self.assertEqual(6.9, imdb_tsv.get_rating(three_little_words))
        self.assertEqual(6.6, imdb_tsv.get_rating(the_mirror_has_two_faces))

    def test_order(self):
        g = self.make_graph()

        e = g.edges[(PersonNode(1), WorkNode(43044))]
        self.assertEqual(1, imdb_tsv.get_order(e))

        e = g.edges[(PersonNode(1), WorkNode(50419))]
        self.assertEqual(2, imdb_tsv.get_order(e))

        e = g.edges[(PersonNode(2), WorkNode(117057))]
        self.assertEqual(3, imdb_tsv.get_order(e))

        e = g.edges[(PersonNode(861703), WorkNode(43044))]
        self.assertEqual(5, imdb_tsv.get_order(e))
