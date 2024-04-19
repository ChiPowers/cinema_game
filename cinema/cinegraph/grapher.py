import networkx as nx

from cinema.cinegraph.node_types import PersonNode, WorkNode

verbose = False


def blurt(s):
    if verbose:
        print(s)


def add_arc(g: nx.Graph, work, person, job=None):
    """
    Add an edge between a work and a person in a professional graph. Add movie and person as nodes if not already in
    graph. A person can be added multiple times to the same work with different jobs by calling this function multiple
    times.
    :param g: graph
    :param work: id for professional work such as a movie, document or music album
    :param person: id for a person participating in producing a work
    :param job: the job performed by person in work
    """
    blurt("{} to {}".format(work, person))
    work = WorkNode(work)
    person = PersonNode(person)
    if work not in g.nodes:
        g.add_node(work)
    if person not in g.nodes:
        g.add_node(person)
    if (work, person) not in g.edges:
        g.add_edge(work, person, job=set())
    if job is not None:
        g.edges[(work, person)]["job"].add(job)


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
    """
    If objs is a list of objects, return those objects without alteration. If objs is a comma separated string, spit
    the string and attempt to get the objects corresponding to string parts interpreted as ids using getter.
    :param objs: A list of objects or a comma separated string of ids.
    :param getter: A function for looking up objects by ids.
    :return: A list of objects
    """
    blurt("interpreting {}".format(objs))
    if type(objs) is str:
        return try_get_objects(objs, getter)
    return objs


class GraphMaker:
    """
    Utility class for appending connections to a professional graph.
    """

    def __init__(self, ia, g: nx.Graph = None):
        """
        Initializer
        :param ia: database of professional works. Could be imdbpy imdb object for example.
        :param g: A graph. If none, initializer will create a graph.
        """
        self.depth_record = dict()
        self.ia = ia
        if g is None:
            g = nx.Graph()
        self.g = g

    def people_from_work(self, work):
        """
        Look up people contributing to a work.
        :param work: id of a work, movie, document or album from a professional database
        :return: List of people objects.
        """
        raise NotImplementedError()

    def works_from_person(self, person):
        """
        Look up works to which person has contributed as a collaborator of some sort.
        :param person: is of person in a database
        :return: List of work objects.
        """
        raise NotImplementedError()

    def traverse_from_person(self, person, depth):
        """
        Add nodes and edges to a professional graph up to depth works started with person and all works to which that
        person has contributed.
        :param person: id of person in database
        :param depth: depth for which to travers professional graph. Stop if less than zero
        """
        if depth <= 0:
            blurt("done")
            return

        blurt("person {} depth {}".format(person, depth))

        for work in self.works_from_person(person):
            self.traverse_from_work(work, depth)

    def traverse_from_work(self, work, depth):
        """
        Add nodes and edges to a professional graph up to depth works started with a work and all collaborators on that
        work.
        :param work: id of work in database
        :param depth: depth for which to travers professional graph. Stop if less than zero
        """
        if depth <= 0:
            blurt("done")
            return

        blurt("work {} depth {}".format(work, depth))

        if work not in self.depth_record:
            self.depth_record[work] = depth
        else:
            if depth > self.depth_record[work]:
                self.depth_record[work] = depth
            else:
                blurt("already explored")
                return

        people_jobs = self.people_from_work(work)

        for person, job in people_jobs:
            add_arc(self.g, work, person, job=job)

        for person, _ in people_jobs:
            self.traverse_from_person(person, depth - 1)

    def traverse(self, depth, works=None, people=None):
        """
        Populate graph starting at possibly multiple works.
        :param depth: depth to which to populate graph from starting works and collaborators
        :param works: None or a list of ids for works
        :param people: None or a list of ids for people
        """
        if works is not None:
            for work in works:
                self.traverse_from_work(work, depth)
        if people is not None:
            for person in people:
                self.traverse_from_person(person, depth)
