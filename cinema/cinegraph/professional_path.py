import networkx as nx


def professional_subgraph(g : nx.Graph, jobs):
    """
    Get edge subgraph containing where work nodes are connected only by collaborators with particular jobs.
    For example, if the professional graph is one where words are movies and collaborators are actors, directors and
    writers, this function can be used to find the subgraph connected by actors.
    :param g: professional bipartite graph
    :param jobs: those jobs we want in the subgraph
    :return: an edge subgraph of g
    """
    jobs = set(jobs)
    edges = [edge for edge in g.edges if not jobs.isdisjoint(g.edges[edge]['job'])]
    return g.edge_subgraph(edges)


def path_details(path, get_person, get_work):
    details = []
    for node in path:
        if node.is_person:
            details.append(get_person(node.id))
        else:
            details.append(get_work(node.id))
    return details
