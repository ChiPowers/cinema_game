import numpy as np
import networkx as nx


def make_game_by_iteration(
    g: nx.Graph, candidates, distance, r: np.random.RandomState = None, max_iter=100
):
    candidates = list(candidates)
    if r is None:
        r = np.random.RandomState()
    a = r.choice(candidates)
    b = a
    d0 = 0
    for _ in range(max_iter):
        c, d = r.choice(candidates, 2, replace=False)
        d1 = nx.shortest_path_length(g, c, d)
        if 2 * distance >= d1 > d0:
            a, b = c, d
            d0 = d1
        if d0 == 2 * distance:
            break
    return a, b
