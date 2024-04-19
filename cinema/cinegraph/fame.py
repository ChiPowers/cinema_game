import networkx as nx
import numpy as np

from cinema.cinegraph.node_types import PersonNode


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
    return {neighbor: feature for neighbor, feature in features if feature is not None}


murdock_exponent = -0.77


def normalized_exponential_decay(n, exponent=murdock_exponent):
    x = np.exp(exponent * np.array(range(n)))
    return x / x.sum()


def weight_zero(g, weight="weight"):
    for edge in g.edges:
        g.edges[edge][weight] = 0


def weight_by_cast_order(g, ia_s3, weight="weight"):
    d = dict()

    for node in get_works(g):
        movie = ia_s3.get_movie(node.id)
        cast = movie["cast"]
        x = normalized_exponential_decay(len(cast))
        for i, actor in enumerate(cast):
            edge = (PersonNode(actor.getID()), node)
            d[edge] = x[i]

    weight_zero(g, weight=weight)

    for edge, w in d.items():
        g.edges[edge][weight] = w


def weight_by_order(g, nodes, sort_nodes):
    for node in nodes:
        neighbors = list(g.neighbors(node))
        sort_nodes(neighbors)
        x = normalized_exponential_decay(len(neighbors))
        for i, neighbor in enumerate(neighbors):
            edge = (node, neighbor)
            g.edges[edge]["weight"] = x[i]


def weight_by_feature_order(g, nodes, get_feature):
    def sort_by_feature(neighbors):
        neighbors.sort(key=get_feature, reverse=True)

    weight_by_order(g, nodes, sort_by_feature)


def person_work(edge):
    if edge[0].is_person:
        p, w = edge
    else:
        w, p = edge
    return p, w


def weight_by_function(g, f, weight="weight"):
    weight_zero(g, weight=weight)
    for edge in g.edges:
        p, w = person_work(edge)
        g.edges[edge][weight] = f(p, w)
