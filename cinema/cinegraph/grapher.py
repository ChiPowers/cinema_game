import networkx as nx


verbose = False


def blurt(s):
    if verbose:
        print(s)


def add_arc(g: nx.Graph, movie, person, job=None):
    blurt("{} to {}".format(movie, person))
    if movie not in g.nodes:
        g.add_node(movie, t="movie")
    if person not in g.nodes:
        g.add_node(person, t="person")
    if (movie, person) not in g.edges:
        g.add_edge(movie, person, job=set())
    if job is not None:
        g.edges[(movie, person)]["job"].add(job)


def try_get(id, getter):
    try:
        return getter(id)
    except ValueError as e:
        blurt(e)


def try_get_objects(ids: str, getter):
    rv = []
    for id in ids.split(","):
        obj = try_get(id, getter)
        if obj is not None:
            rv.append(obj)
    return rv


def interpret_objects(objs, getter):
    blurt("interpreting {}".format(objs))
    if type(objs) is str:
        return try_get_objects(objs, getter)
    return objs


class GraphMaker:
    def __init__(self, ia, g: nx.Graph = None):
        self.depth_record = dict()
        self.ia = ia
        if g is None:
            g = nx.Graph()
        self.g = g

    def people_from_movie(self, movie):
        raise NotImplementedError()

    def movies_from_person(self, person):
        raise NotImplementedError()

    def traverse_from_person(self, person, depth):
        if depth < 0:
            blurt("done")
            return
        self.ia.update(person, info="main")
        for movie in self.movies_from_person(person):
            self.traverse_from_movie(movie, depth)

    def traverse_from_movie(self, movie, depth):
        if depth < 0:
            blurt("done")
            return
        blurt("movie \"{}\" depth {}".format(movie, depth))
        people_jobs = self.people_from_movie(movie)

        for person, job in people_jobs:
            add_arc(self.g, movie.getID(), person.getID(), job=job)

        if movie.getID() not in self.depth_record:
            self.depth_record[movie.getID()] = depth
        else:
            if depth > self.depth_record[movie.getID()]:
                self.depth_record[movie.getID()] = depth
                for person, _ in people_jobs:
                    self.traverse_from_person(person, depth - 1)

    def traverse(self, depth, movies=None, people=None):
        if movies is not None:
            for movie in movies:
                self.traverse_from_movie(movie, depth)
        if people is not None:
            for person in people:
                self.traverse_from_person(person, depth)


class S3GraphMaker(GraphMaker):
    def __init__(self, ia, g: nx.Graph = None):
        GraphMaker.__init__(self, ia, g=g)

    def people_from_movie(self, movie):
        people_jobs = []

        def append(people, job):
            for person in people:
                people_jobs.append((person, job))

        if "cast" in movie:
            cast = interpret_objects(movie["cast"], self.ia.get_person)
            append(cast, "actor")
        if "writer" in movie:
            writers = interpret_objects(movie["writer"], self.ia.get_person)
            append(writers, "writer")
        if "director" in movie:
            directors = interpret_objects(movie["director"], self.ia.get_person)
            append(directors, "director")
        if "producer" in movie:
            producers = interpret_objects(movie["producer"], self.ia.get_person)
            append(producers, "producer")
        return people_jobs

    def movies_from_person(self, person):
        if "known for" in person:
            return interpret_objects(person["known for"], self.ia.get_movie)
        return []


