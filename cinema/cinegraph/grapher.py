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


def traverse_s3(g: nx.Graph, ia, depth, movies=None, people=None):
    if movies is not None:
        for movie in movies:
            traverse_s3_from_movie(g, ia, depth, movie)
    if people is not None:
        for person in people:
            traverse_s3_from_person(g, ia, depth, person)


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


def is_actress(person):
    if "primary profession" in person:
        return "actress" in person["primary profession"].split(",")
    blurt("{} has not primary profession".format(person.getID()))
    return False


def traverse_s3_from_movie(g: nx.Graph, ia, depth, movie):
    blurt("movie {} depth {}".format(movie, depth))
    if depth < 0:
        blurt('done')
        return
    if "cast" in movie:
        cast = interpret_objects(movie["cast"], ia.get_person)
        for person in cast:
            job = "actress" if is_actress(person) else "actor"
            add_arc(g, movie.getID(), person.getID(), job=job)
            traverse_s3_from_person(g, ia, depth - 1, person)
    if "writer" in movie:
        for writer in interpret_objects(movie["writer"], ia.get_person):
            add_arc(g, movie.getID(), writer.getID(), job="writer")
            traverse_s3_from_person(g, ia, depth - 1, writer)
    if "director" in movie:
        for director in interpret_objects(movie["director"], ia.get_person):
            add_arc(g, movie.getID(), director.getID(), job="director")
            traverse_s3_from_person(g, ia, depth - 1, director)
    if "producer" in movie:
        for producer in interpret_objects(movie["producer"], ia.get_person):
            add_arc(g, movie.getID(), producer.getID(), job="producer")
            traverse_s3_from_person(g, ia, depth - 1, producer)


def traverse_s3_from_person(g: nx.Graph, ia, depth, person):
    blurt("person {} depth {}".format(person, depth))
    ia.update(person, info='main')
    if "known for" in person:
        for movie in interpret_objects(person["known for"], ia.get_movie):
            blurt(movie)
            ia.update(movie, info='main')
            if movie.getID() not in g.nodes:
                traverse_s3_from_movie(g, ia, depth, movie)
            else:
                blurt("already processed {}".format(movie))
