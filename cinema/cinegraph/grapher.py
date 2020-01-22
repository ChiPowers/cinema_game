import networkx as nx


def add_arc(g: nx.Graph, movie, person, job=None):
    if movie not in g.nodes:
        g.add_node(movie, t="movie")
    if person not in g.nodes:
        g.add_node(person, t="person")
    if (movie, person) not in g.edges:
        g.add_edge(movie, person, job=set())
    if job is not None:
        g.edges[(movie, person)]["job"].add(job)
