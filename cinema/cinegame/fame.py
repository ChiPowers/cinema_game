import networkx as nx
import numpy as np

from cinema.cinegraph.grapher import PersonNode


def get_people(g):
    return [node for node in g.nodes if node.is_person]


def get_works(g):
    return [node for node in g.nodes if not node.is_person]


def sort_by_fame(nodes_fame):
    nodes_fame.sort(key=lambda node_fame: node_fame[1], reverse=True)


def fame_by_number_of_works(g: nx.Graph, people=None):
    if people is None:
        people = get_people(g)
    people_degree = [(person, g.degree(person)) for person in people]
    sort_by_fame(people_degree)
    return people_degree


def fame_by_pagerank(g: nx.Graph, people=None, pagerank=None):
    if people is None:
        people = get_people(g)
    if pagerank is None:
        pagerank = nx.pagerank(g)
    people_pagerank = [(person, pagerank[person]) for person in people]
    sort_by_fame(people_pagerank)
    return people_pagerank, pagerank


def works_by_pagerank(g: nx.Graph, works=None, pagerank=None):
    if works is None:
        works = get_works(g)
    if pagerank is None:
        pagerank = nx.pagerank(g)
    works_pagerank = [(work, pagerank[work]) for work in works]
    sort_by_fame(works_pagerank)
    return works_pagerank, pagerank


def neighbor_features(g: nx.Graph, node, get_feature):
    features = [(neighbor, get_feature(neighbor)) for neighbor in g.neighbors(node)]
    return {
        neighbor: feature for neighbor, feature in features if feature is not None
    }



murdock_exponent = -0.77


def normalized_exponential_decay(n, exponent=murdock_exponent):
    x = np.exp(exponent * np.array(range(n)))
    return x / x.sum()
