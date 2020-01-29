import networkx as nx

from cinema.cinegraph.grapher import GraphMaker, interpret_objects, blurt

class S3GraphMaker(GraphMaker):
    """
    Implementation of GraphMaker in which ia is a database connection for imbdpy imdb connecting to a local database
    populated from s3 data.
    See https://imdbpy.readthedocs.io/en/latest/usage/s3.html
    """

    def __init__(self, ia, g: nx.Graph = None):
        GraphMaker.__init__(self, ia, g=g)

    def people_from_work(self, work):
        work = self.ia.get_movie(work)
        if 'title' in work:
            blurt(work['title'])
        people_jobs = []

        def append(people, job):
            for person in people:
                people_jobs.append((person.getID(), job))

        if "cast" in work:
            cast = interpret_objects(work["cast"], self.ia.get_person)
            append(cast, "actor")
        if "writer" in work:
            writers = interpret_objects(work["writer"], self.ia.get_person)
            append(writers, "writer")
        if "director" in work:
            directors = interpret_objects(work["director"], self.ia.get_person)
            append(directors, "director")
        if "producer" in work:
            producers = interpret_objects(work["producer"], self.ia.get_person)
            append(producers, "producer")
        return people_jobs

    def works_from_person(self, person):
        person = self.ia.get_person(person, info="main")
        if 'name' in person:
            blurt(person['name'])
        works = []
        if "known for" in person:
            works = interpret_objects(person["known for"], self.ia.get_movie)
        return [work.getID() for work in works]
