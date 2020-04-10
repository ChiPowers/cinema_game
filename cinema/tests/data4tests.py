import pickle
import numpy as np
from cinema import directories
from cinema.cinegraph.grapher import PersonNode, WorkNode


class MockImdbObject(dict):
    def __init__(self, *args, default=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default = default

    def __missing__(self, key):
        return self.default

    def getID(self):
        return self["id"]

    @property
    def r(self):
        return np.random.RandomState(self.getID())

    @staticmethod
    def mock_object(node):
        m = MockImdbObject()
        m["id"] = node.id
        return m

    @staticmethod
    def mock_actor(person_node):
        p = MockImdbObject.mock_object(person_node)
        p["name"] = str(p.getID())
        pay = 100 * p.r.rand()
        p["pay"] = pay
        return p

    @staticmethod
    def mock_known_for(p, person_node, g):
        # Those actors who earn less than 10 will be known for nothing
        if p["pay"] > 10:
            # known for top four movies by rating
            movies = [
                MockImdbObject.mock_movie(movie) for movie in g.neighbors(person_node)
            ]
            movies.sort(key=lambda m: m["rating"], reverse=True)
            p["known for"] = list(movies[:4])

    @staticmethod
    def mock_movie(movie_node):
        m = MockImdbObject.mock_object(movie_node)
        m["title"] = str(m.getID())
        r = m.r
        m["votes"] = r.randint(1, 1000)
        m["rating"] = 10 * r.rand()
        return m

    @staticmethod
    def mock_cast(m, movie_node, g):
        # cast is top four actors by pay
        actors = [MockImdbObject.mock_actor(movie) for movie in g.neighbors(movie_node)]
        actors.sort(key=lambda a: a["pay"], reverse=True)
        m["cast"] = list(actors[:4])


class MockIMBD:
    def __init__(self, g):
        self.g = g

    def get_person(self, id):
        person_node = PersonNode(id)
        p = MockImdbObject.mock_actor(person_node)
        MockImdbObject.mock_known_for(p, person_node, self.g)
        return p

    def get_movie(self, id):
        movie_node = WorkNode(id)
        m = MockImdbObject.mock_movie(movie_node)
        MockImdbObject.mock_cast(m, movie_node, self.g)
        return m


# Kevin Bacon
def get_bacon(ia=None):
    return ia.get_person("0000102", info=("main", "filmography", "biography"))


# Natalie Portman
def get_natalie(ia=None):
    return ia.get_person("0000204", info=("main", "filmography", "biography"))


# Sarah Michelle Gellar
def get_sarah(ia=None):
    return ia.get_person("0001264", info=("main", "filmography", "biography"))


# The Air I Breath
def get_air(ia=None):
    return ia.get_movie("0485851")


# A Powerful Noise Live
def get_noise(ia=None):
    return ia.get_movie("1392211")


def get_small_graph():
    path = directories.test("small_professional_graph.pkl")
    with open(path, "rb") as f:
        return pickle.load(f)
