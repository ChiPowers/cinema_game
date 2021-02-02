from django.test import TestCase

import networkx as nx

from cinema.cinegraph.grapher import PersonNode, WorkNode
from cinema.cinegraph import imdb_tsv


class TestIMDbTsv(TestCase):
    def setUp(self):
        self.names = [
            {
                "deathYear": "1987",
                "primaryName": "Fred Astaire",
                "nconst": "nm0000001",
                "birthYear": "1899",
                "knownForTitles": "tt0072308,tt0050419,tt0043044,tt0053137",
                "primaryProfession": "soundtrack,actor,miscellaneous",
            },
            {
                "deathYear": "2014",
                "primaryName": "Lauren Bacall",
                "nconst": "nm0000002",
                "birthYear": "1924",
                "knownForTitles": "tt0117057,tt0037382,tt0038355,tt0071877",
                "primaryProfession": "actress,soundtrack",
            },
            {
                "deathYear": "\\N",
                "primaryName": "Brigitte Bardot",
                "nconst": "nm0000003",
                "birthYear": "1934",
                "knownForTitles": "tt0049189,tt0059956,tt0057345,tt0054452",
                "primaryProfession": "actress,soundtrack,producer",
            },
            {
                "primaryName": "Richard Thorpe",
                "knownForTitles": "tt0015852,tt0044760,tt0043599,tt0045966",
                "deathYear": "1991",
                "primaryProfession": "director,writer,actor",
                "nconst": "nm0861703",
                "birthYear": "1896",
            },
        ]
        self.basics = [
            {
                "runtimeMinutes": "102",
                "isAdult": 0,
                "tconst": "tt0043044",
                "genres": "Biography,Comedy,Musical",
                "endYear": "\\N",
                "originalTitle": "Three Little Words",
                "primaryTitle": "Three Little Words",
                "startYear": "1950",
                "titleType": "movie",
            },
            {
                "runtimeMinutes": "103",
                "isAdult": 0,
                "tconst": "tt0050419",
                "genres": "Comedy,Musical,Romance",
                "endYear": "\\N",
                "originalTitle": "Funny Face",
                "primaryTitle": "Funny Face",
                "startYear": "1957",
                "titleType": "movie",
            },
            {
                "runtimeMinutes": "134",
                "isAdult": 0,
                "tconst": "tt0053137",
                "genres": "Drama,Romance,Sci-Fi",
                "endYear": "\\N",
                "originalTitle": "On the Beach",
                "primaryTitle": "On the Beach",
                "startYear": "1959",
                "titleType": "movie",
            },
            {
                "isAdult": 0,
                "runtimeMinutes": "126",
                "genres": "Comedy,Drama,Romance",
                "titleType": "movie",
                "endYear": "\\N",
                "tconst": "tt0117057",
                "primaryTitle": "The Mirror Has Two Faces",
                "startYear": "1996",
                "originalTitle": "The Mirror Has Two Faces",
            },
        ]
        self.ratings = [
            {"averageRating": 6.9, "tconst": "tt0043044", "numVotes": 1497},
            {"averageRating": 7.0, "tconst": "tt0050419", "numVotes": 24896},
            {"averageRating": 7.2, "tconst": "tt0053137", "numVotes": 11261},
            {"averageRating": 6.9, "tconst": "tt0072308", "numVotes": 36833},
            {"tconst": "tt0117057", "numVotes": 14369, "averageRating": 6.6},
        ]
        self.principals = [
            {
                "ordering": 10,
                "job": "\\N",
                "tconst": "tt0043044",
                "nconst": "nm0943978",
                "category": "actor",
                "characters": '["Charlie Kope"]',
            },
            {
                "category": "director",
                "ordering": 5,
                "characters": "\\N",
                "tconst": "tt0043044",
                "nconst": "nm0861703",
                "job": "\\N",
            },
            {
                "ordering": 1,
                "job": "\\N",
                "tconst": "tt0043044",
                "nconst": "nm0000001",
                "category": "actor",
                "characters": '["Bert Kalmar"]',
            },
            {
                "ordering": 1,
                "job": "\\N",
                "tconst": "tt0050419",
                "nconst": "nm0000030",
                "category": "actress",
                "characters": '["Jo Stockton"]',
            },
            {
                "ordering": 2,
                "job": "\\N",
                "tconst": "tt0050419",
                "nconst": "nm0000001",
                "category": "actor",
                "characters": '["Dick Avery"]',
            },
            {
                "ordering": 9,
                "job": "screenplay",
                "tconst": "tt0072308",
                "nconst": "nm0798103",
                "category": "writer",
                "characters": "\\N",
            },
            {
                "category": "actress",
                "ordering": 3,
                "characters": '["Hannah Morgan"]',
                "tconst": "tt0117057",
                "nconst": "nm0000002",
                "job": "\\N",
            },
        ]

    def tearDown(self):
        pass

    def make_graph(self):
        g = nx.Graph()
        for person in self.names:
            imdb_tsv.addPerson(g, person)
        for work in self.basics:
            imdb_tsv.addWork(g, work)
        for rating in self.ratings:
            imdb_tsv.updateRating(g, rating)
        for credit in self.principals:
            imdb_tsv.addContribution(g, credit)
        return g

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
        imdb_tsv.addPerson(g, self.names[0])
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
        imdb_tsv.addWork(g, self.basics[0])
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
        imdb_tsv.addWork(g, self.basics[0])
        imdb_tsv.updateRating(g, self.ratings[0])
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
        expected = {"contributions": {"actor": {"ordering": 1, "job": "\\N"}}}
        actual = g.edges[(PersonNode(1), WorkNode(43044))]
        self.assertEqual(expected, actual)

    def test_has_profession(self):
        g = self.make_graph()
        self.assertFalse(imdb_tsv.hasProfession(g, PersonNode(8888888888), "actor"))
        self.assertFalse(imdb_tsv.hasProfession(g, PersonNode(1), "producer"))
        self.assertTrue(imdb_tsv.hasProfession(g, PersonNode(3), "producer"))

    def test_is_actor(self):
        g = self.make_graph()
        self.assertTrue(imdb_tsv.isActor(g, PersonNode(1)))
        self.assertFalse(imdb_tsv.isActor(g, PersonNode(2)))
        self.assertFalse(imdb_tsv.isActor(g, PersonNode(3)))

    def test_is_actress(self):
        g = self.make_graph()
        self.assertFalse(imdb_tsv.isActress(g, PersonNode(1)))
        self.assertTrue(imdb_tsv.isActress(g, PersonNode(2)))
        self.assertTrue(imdb_tsv.isActress(g, PersonNode(3)))

    def test_contributed_as(self):
        g = self.make_graph()
        thorpe = PersonNode(861703)
        three_little_words = WorkNode(43044)
        the_mirror_has_two_faces = WorkNode(117057)
        self.assertIn(three_little_words, g.nodes)
        self.assertIn((thorpe, three_little_words), g.edges)
        self.assertTrue(imdb_tsv.contributedAs(g, thorpe, three_little_words, 'director'))
        self.assertFalse(imdb_tsv.contributedAs(g, thorpe, three_little_words, 'cook'))
        self.assertFalse(imdb_tsv.contributedAs(g, thorpe, the_mirror_has_two_faces, 'director'))

    def test_acted_in(self):
        g = self.make_graph()
        thorpe = PersonNode(861703)
        astaire = PersonNode(1)
        bacall = PersonNode(2)
        three_little_words = WorkNode(43044)
        the_mirror_has_two_faces = WorkNode(117057)
        self.assertFalse(imdb_tsv.actedIn(g, thorpe, three_little_words))
        self.assertFalse(imdb_tsv.actedIn(g, thorpe, the_mirror_has_two_faces))
        self.assertTrue(imdb_tsv.actedIn(g, astaire, three_little_words))
        self.assertFalse(imdb_tsv.actedIn(g, astaire, the_mirror_has_two_faces))
        self.assertFalse(imdb_tsv.actedIn(g, bacall, three_little_words))
        self.assertTrue(imdb_tsv.actedIn(g, bacall, the_mirror_has_two_faces))
