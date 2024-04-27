from typing import Iterable

import numpy as np
import networkx as nx

from cinema.cinegraph.node_types import ProfessionalNode, PersonNode, WorkNode


class CandidateNotFoundException(Exception):
    pass


class GameNotFoundException(Exception):
    pass


def select_random_nodes(
    nodes: Iterable[ProfessionalNode],
    size=1,
    replace: bool = False,
    r: np.random.RandomState = None,
):
    nodes = list(nodes)
    nodes.sort(key=repr)
    return r.choice(nodes, size=size, replace=replace)


def make_people_subgraph(g: nx.Graph, people: Iterable[PersonNode]):
    people = set(people)
    works = [node for node in g.nodes if not node.is_person and not people.isdisjoint(g.neighbors(node))]
    nodes = people.union(works)
    return g.subgraph(nodes)


def make_game_from_starting_node(
    g: nx.Graph, start, candidates, distance, r: np.random.RandomState = None
):
    candidates = set(candidates)
    if r is None:
        r = np.random.RandomState()

    outer_ego_graph = nx.ego_graph(g, start, radius=2 * distance)
    inner_ego_graph = nx.ego_graph(outer_ego_graph, start, radius=2 * distance - 1)

    candidates.intersection_update(outer_ego_graph.nodes)
    candidates.difference_update(inner_ego_graph.nodes)

    if len(candidates) == 0:
        raise CandidateNotFoundException()

    end, = select_random_nodes(candidates, r=r)

    return start, end


def make_game_by_iteration(
    g: nx.Graph, candidates, distance, r: np.random.RandomState = None, max_iter=100
):
    candidates = list(candidates)
    if r is None:
        r = np.random.RandomState()
    for _ in range(max_iter):
        try:
            return make_game_from_starting_node(g, r.choice(candidates), candidates, distance, r)
        except CandidateNotFoundException:
            continue

    raise GameNotFoundException()



class GameMaker:
    candidates: set[PersonNode]
    g: nx.Graph

    def __init__(self, g: nx.Graph, candidates: Iterable[PersonNode]):
        self.g = make_people_subgraph(g, candidates)
        self.candidates = set(candidates)

    def make_game(self, distance, r: np.random.RandomState = None) -> tuple[PersonNode, PersonNode]:
        return make_game_by_iteration(self.g, self.candidates, distance, r=r)

