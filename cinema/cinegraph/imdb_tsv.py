import pandas as pd

from cinema import directories
from cinema.cinegraph.grapher import PersonNode, WorkNode


class IMDbPersonNode(PersonNode):
    def __init__(self, nconst):
        PersonNode.__init__(self, int(nconst[2:]))


class IMDbWorkNode(WorkNode):
    def __init__(self, tconst):
        WorkNode.__init__(self, int(tconst[2:]))


def load_names():
    return pd.read_csv(
        directories.data("name.basics.tsv.gz"), compression="gzip", sep="\t"
    )


def load_basics():
    return pd.read_csv(
        directories.data("title.basics.tsv.gz"),
        compression="gzip",
        sep="\t",
        low_memory=False,
    )


def load_ratings():
    return pd.read_csv(
        directories.data("title.ratings.tsv.gz"), compression="gzip", sep="\t"
    )


def load_principals():
    return pd.read_csv(
        directories.data("title.principals.tsv.gz"), compression="gzip", sep="\t"
    )


def add_person(g, row):
    person = IMDbPersonNode(row["nconst"])
    try:
        known = {IMDbWorkNode(tt) for tt in row["knownForTitles"].split(",")}
    except ValueError as err:
        known = {}
    try:
        professions = set(row["primaryProfession"].split(","))
    except AttributeError as err:
        professions = {}
    g.add_node(
        person,
        name=row["primaryName"],
        birth=row["birthYear"],
        death=row["deathYear"],
        professions=professions,
        known=known,
    )


def add_work(g, row):
    work = IMDbWorkNode(row["tconst"])
    try:
        genres = set(row["genres"].split(","))
    except AttributeError as err:
        genres = {}
    g.add_node(
        work,
        title=row["primaryTitle"],
        adult=row["isAdult"],
        start=row["startYear"],
        end=row["endYear"],
        runtime=row["runtimeMinutes"],
        genres=genres,
    )


def update_rating(g, row):
    work = IMDbWorkNode(row["tconst"])
    if work not in g:
        return
    update = {"rating": row["averageRating"], "votes": row["numVotes"]}
    g.nodes[work].update(update)


def add_contribution(g, row):
    person = IMDbPersonNode(row["nconst"])
    work = IMDbWorkNode(row["tconst"])
    if not (person in g.nodes and work in g.nodes):
        return
    contribution = {"job": row["job"]}
    contributions = {row["category"]: contribution}
    if (person, work) in g.edges:
        g.edges[(person, work)]["contributions"].update(contributions)
    else:
        g.add_edge(person, work, contributions=contributions)
    g.edges[(person, work)]["ordering"] = row["ordering"]


def has_profession(n, profession):
    return profession in n["professions"]


def is_actor(n):
    return has_profession(n, "actor")


def is_actress(n):
    return has_profession(n, "actress")


def did_acting(n):
    return is_actor(n) or is_actress(n)


def contributed_as(e, profession):
    return profession in e["contributions"].keys()


def acted_in(e):
    return contributed_as(e, "actor") or contributed_as(e, "actress")


def get_order(e):
    if "ordering" not in e:
        return 10
    return min(10, e["ordering"])


def get_rating(n):
    if "rating" not in n:
        return 0
    return n["rating"]


def get_votes(n):
    if "votes" not in n:
        return 0
    return n["votes"]


def apply_to_node_in_graph(g, n, f):
    if n not in g.nodes:
        return False
    return f(g.nodes[n])


def apply_to_edge_in_graph(g, e, f):
    if e not in g.edges:
        return False
    return f(g.edges[e])


def has_profession_in_graph(g, p, profession):
    return apply_to_node_in_graph(g, p, lambda n: has_profession(n, profession))


def is_actor_in_graph(g, p):
    return apply_to_node_in_graph(g, p, is_actor)


def is_actress_in_graph(g, p):
    return apply_to_node_in_graph(g, p, is_actress)


def did_acting_in_graph(g, p):
    return apply_to_node_in_graph(g, p, did_acting)


def contributed_as_in_graph(g, p, t, profession):
    return apply_to_edge_in_graph(g, (p, t), lambda e: contributed_as(e, profession))


def acted_in_in_graph(g, p, t):
    return apply_to_edge_in_graph(g, (p, t), acted_in)
