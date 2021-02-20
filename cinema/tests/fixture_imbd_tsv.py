import networkx as nx

from cinema.cinegraph import imdb_tsv


class FixtureIMDbTsv:
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

    def make_graph(self):
        g = nx.Graph()
        for person in self.names:
            imdb_tsv.add_person(g, person)
        for work in self.basics:
            imdb_tsv.add_work(g, work)
        for rating in self.ratings:
            imdb_tsv.update_rating(g, rating)
        for credit in self.principals:
            imdb_tsv.add_contribution(g, credit)
        return g
