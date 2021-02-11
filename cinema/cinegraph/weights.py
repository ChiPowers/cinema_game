import math
import numpy as np

from cinema.cinegraph import fame
from cinema.cinegraph import imdb_tsv


def credit_order_weight(order):
    return math.tanh((1 - order) / 3) + 1


def rating_weight(rating):
    return rating / 10.0


def normalized_activation(y):
    return 0.5 * (math.tanh(y) + 1)


def node_mean_std(g, f, pred):
    x = np.array([f(g.nodes[n]) for n in g.nodes if pred(n, g.nodes[n])])
    return np.mean(x), np.std(x)


def votes_mean_std(g, get_votes=imdb_tsv.get_votes):
    return node_mean_std(g, get_votes, lambda n, _: not n.is_person)


def weight_by_normalized_votes(g, get_votes=imdb_tsv.get_votes, weight="weight"):
    mu, sigma = votes_mean_std(g, get_votes=get_votes)
    fame.weight_by_function(
        g,
        lambda p, w: normalized_activation((get_votes(g.nodes[w]) - mu) / sigma),
        weight=weight,
    )


def weight_only_actors(g, weight="weight", acted_in=imdb_tsv.acted_in):
    fame.weight_by_function(g, lambda p, w: acted_in(g.edges[(p, w)]), weight=weight)


def weight_credit_order(g, get_order=imdb_tsv.get_order, weight="weight"):
    fame.weight_by_function(
        g, lambda p, w: credit_order_weight(get_order(g.edges[(p, w)])), weight=weight
    )


def weight_by_rating(g, get_order=imdb_tsv.get_rating, weight="weight"):
    fame.weight_by_function(
        g, lambda p, w: rating_weight(get_order(g.nodes[w])), weight=weight
    )


def combine_weights(g, binary_op, weight0, weight1, new_weight=None):
    if new_weight is None:
        new_weight = "{}_{}".format(weight0, weight1)
    for edge in g.edges:
        g.edges[edge][new_weight] = binary_op(
            g.edges[edge][weight0], g.edges[edge][weight1]
        )
    return new_weight


def sum_weights(g, weight0, weight1, new_weight=None):
    return combine_weights(
        g, lambda a, b: a + b, weight0, weight1, new_weight=new_weight
    )


def multiply_weights(g, weight0, weight1, new_weight=None):
    return combine_weights(
        g, lambda a, b: a * b, weight0, weight1, new_weight=new_weight
    )
