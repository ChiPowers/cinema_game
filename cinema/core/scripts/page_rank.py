# scripts/page_rank.py
# Compute PageRank of professional graph constructed by make_imdb_professional_graph

import networkx as nx
import pickle
import time

from cinema.cinegraph import weights
from cinema import directories


def full_graph_pr(g):
    return nx.pagerank(g)


def actor_graph_pr(g):
    weight = "actor_weight"
    weights.weight_only_actors(g, weight=weight)
    return nx.pagerank(g, weight=weight)


def credit_order_pr(g):
    weight = "order_weight"
    weights.weight_credit_order(g, weight=weight)
    return nx.pagerank(g, weight=weight)


def rating_pr(g):
    weight = "rating_weight"
    weights.weight_by_rating(g, weight=weight)
    return nx.pagerank(g, weight=weight)


def votes_pr(g):
    weight = "votes_weight"
    weights.weight_by_normalized_votes(g, weight=weight)
    return nx.pagerank(g, weight=weight)


def rating_votes_pr(g):
    weight = "ratings_votes_weight"
    weights.multiply_weights(
        g, weight0="rating_weight", weight1="votes_weight", new_weight=weight
    )
    return nx.pagerank(g, weight=weight)


def show_person(g, rank, p, i):
    n = g.nodes[p]
    s = "{:>3} {:7.2e} {:>8} {:<25} birth {:>4} death {:>4}, {}".format(
        i, rank[p], p.id, n["name"], n["birth"], n["death"], n["professions"]
    )
    print(s)


def compute_pagerank(g, pageranker, name: str):
    filename = "{}_pagerank.pkl".format(name.replace(" ", "_"))

    t0 = time.time()
    print("Computing page rank of {}. This may take a bit of time".format(name))
    rank = pageranker(g)
    print("PageRank computed in {:.2g} seconds.".format(time.time() - t0))
    nodes = list(g.nodes)
    nodes.sort(key=lambda n: rank[n], reverse=True)
    people = [n for n in nodes if n.is_person]
    for i, p in enumerate(people[:25]):
        show_person(g, rank, p, i)
    print("Saving page rank dictionary.")
    with open(directories.data(filename), "wb") as f:
        pickle.dump(rank, f)
    print("Saved.\n\n")


def run():
    print("Loading professional graph.")
    with open(directories.data("professional.pkl"), "rb") as f:
        g = pickle.load(f)

    compute_pagerank(g, full_graph_pr, "full graph")
    compute_pagerank(g, actor_graph_pr, "actor graph")
    compute_pagerank(g, credit_order_pr, "credit order graph")
    compute_pagerank(g, rating_pr, "rating graph")
    compute_pagerank(g, votes_pr, "votes graph")
    compute_pagerank(g, rating_votes_pr, "rating and votes graph")
