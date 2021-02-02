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


def addPerson(g, row):
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


def addWork(g, row):
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


def updateRating(g, row):
    work = IMDbWorkNode(row["tconst"])
    if work not in g:
        return
    update = {"rating": row["averageRating"], "votes": row["numVotes"]}
    g.nodes[work].update(update)


def addContribution(g, row):
    person = IMDbPersonNode(row["nconst"])
    work = IMDbWorkNode(row["tconst"])
    if not (person in g.nodes and work in g.nodes):
        return
    contribution = {"ordering": row["ordering"], "job": row["job"]}
    contributions = {row["category"]: contribution}
    if (person, work) in g.edges:
        g.edges[(person, work)]["contributions"].update(contributions)
    else:
        g.add_edge(person, work, contributions=contributions)


def hasProfession(g, p, profession):
    if p not in g.nodes:
        return False
    return profession in g.nodes[p]["professions"]


def isActor(g, p):
    return hasProfession(g, p, "actor")


def isActress(g, p):
    return hasProfession(g, p, "actress")


def didActing(g, p):
    return isActor(g, p) or isActress(g, p)


def contributedAs(g, p, t, profession):
    if (p, t) not in g.edges:
        return False
    return profession in g.edges[(p, t)]["contributions"].keys()


def actedIn(g, p, t):
    return contributedAs(g, p, t, "actor") or contributedAs(g, p, t, "actress")
