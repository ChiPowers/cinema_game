import networkx as nx

from cinema.cinegraph.grapher import GraphMaker, interpret_objects, blurt
from cinema.cinegraph.professional_path import path_details, professional_subgraph


class S3GraphMaker(GraphMaker):
    """
    Implementation of GraphMaker in which ia is a database connection for imbdpy imdb connecting to a local database
    populated from s3 data.
    See https://imdbpy.readthedocs.io/en/latest/usage/s3.html
    """

    def __init__(self, ia, g: nx.Graph = None, just_movies=False):
        GraphMaker.__init__(self, ia, g=g)
        self.just_movies = just_movies

    def people_from_work(self, work):
        work = self.ia.get_movie(work)
        if "title" in work:
            blurt(work["title"])
        people_jobs = []

        def append(people, job):
            for person in people:
                people_jobs.append((person.getID(), job))

        if "cast" in work:
            cast = interpret_objects(work["cast"], self.ia.get_person)
            append(cast, 'actor')
        if "writer" in work:
            writers = interpret_objects(work["writer"], self.ia.get_person)
            append(writers, 'writer')
        if "director" in work:
            directors = interpret_objects(work["director"], self.ia.get_person)
            append(directors, 'director')
        if "producer" in work:
            producers = interpret_objects(work["producer"], self.ia.get_person)
            append(producers, 'producer')
        return people_jobs

    def works_from_person(self, person):
        person = self.ia.get_person(person, info="main")
        if "name" in person:
            blurt(person["name"])
        works = []
        if "known for" in person:
            works = interpret_objects(person["known for"], self.ia.get_movie)
        if self.just_movies:
            works = [
                work for work in works if "kind" in work and work["kind"] == "movie"
            ]
        return [work.getID() for work in works]


def s3_path_details(path, ia):
    return path_details(
        path,
        get_person=lambda id: ia.get_person(id)["name"],
        get_work=lambda id: ia.get_movie(id)["title"],
    )


def s3_kind_annotation(g: nx.Graph, ia):
    for node in g.nodes:
        if not node.is_person:
            work = ia.get_movie(node.id)
            if "kind" in work:
                g.nodes[node]["kind"] = work["kind"]
            else:
                g.nodes[node]["kind"] = "unknown"


def is_movie(g, node):
    return (
        (not node.is_person)
        and "kind" in g.nodes[node]
        and g.nodes[node]["kind"] == "movie"
    )


def movie_actor_subgraph(g):
    movies_and_people = [node for node in g.nodes if node.is_person or is_movie(g, node)]
    movie_graph = g.subgraph(movies_and_people)
    return professional_subgraph(movie_graph, ['actor'])
