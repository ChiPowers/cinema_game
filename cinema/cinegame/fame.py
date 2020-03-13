import networkx as nx


def get_people(g):
    return [node for node in g.nodes if node.is_person]


def fame_by_number_of_works(g: nx.Graph, people=None):
    if people is None:
        people = get_people(g)
    people_degree = [(person, g.degree(person)) for person in people]
    people_degree.sort(key=lambda person_degree: person_degree[1], reverse=True)
    return people_degree


def fame_by_pagerank(g: nx.Graph, people=None, pagerank=None):
    if people is None:
        people = get_people(g)
    if pagerank is None:
        pagerank = nx.pagerank(g)
    people_pagerank = [(person, pagerank[person]) for person in people]
    people_pagerank.sort(key=lambda person_pagerank: person_pagerank[1], reverse=True)
    return people_pagerank, pagerank
