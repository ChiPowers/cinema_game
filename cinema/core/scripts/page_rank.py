# scripts/page_rank.py
# Compute PageRank of professional graph constructed by make_imdb_professional_graph

import networkx as nx
import pickle
import time

from cinema import directories


def full_graph_pr(g):
    return nx.pagerank(g)


def show_person(g, rank, p, i):
    n = g.nodes[p]
    s = "{:>3} {:7.2e} {:>8} {:<25} birth {:>4} death {:>4}, {}".format(
        i, rank[p], p.id, n["name"], n["birth"], n["death"], n["professions"]
    )
    print(s)


def run():
    print("Loading professional graph.")
    with open(directories.data("professional.pkl"), "rb") as f:
        g = pickle.load(f)

    t0 = time.time()
    print("Computing page rank of full graph. This may take a bit of time")
    rank = full_graph_pr(g)
    print("PageRank computed in {:.2g} seconds.".format(time.time() - t0))
    nodes = list(g.nodes)
    nodes.sort(key=lambda n: rank[n], reverse=True)
    people = [n for n in nodes if n.is_person]
    for i, p in enumerate(people[:100]):
        show_person(g, rank, p, i)
    print("Saving page rank dictionary.")
    with open(directories.data("full_graph_pagerank.pkl"), "wb") as f:
        pickle.dump(rank, f)
    print("Ending script.")
