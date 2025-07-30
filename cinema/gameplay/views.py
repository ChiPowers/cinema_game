from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import networkx as nx
import os
import csv
import random

from django.conf import settings

from cinema.cinegame.game import GameGraphAndHTTP
from cinema.cinegraph.node_types import PersonNode, WorkNode

# ==============================
# Load Seed Actors from CSV
# ==============================
SEED_ACTORS_PATH = os.path.join("data", "actors.csv")

def load_seed_actors():
    seed_actors = set()
    if os.path.exists(SEED_ACTORS_PATH):
        with open(SEED_ACTORS_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0].strip():
                    seed_actors.add(row[0].strip())
    return seed_actors

SEED_ACTORS = load_seed_actors()

# ==============================
# Load Graph
# ==============================
def get_graph_and_ia():
    import pickle
    from imdb import IMDb

    graph_path = os.path.join("data", "professional.pkl")
    if not os.path.exists(graph_path):
        raise FileNotFoundError("Graph pickle not found at data/professional.pkl")

    with open(graph_path, "rb") as f:
        g = pickle.load(f)

    ia = IMDb()
    return g, ia

# ==============================
# API ENDPOINTS
# ==============================

@api_view(['GET'])
def start_game(request):
    graph, ia = get_graph_and_ia()

    # Build absolute path to data/actors.csv
    csv_path = os.path.join(settings.BASE_DIR, "data", "actors.csv")

    # Load seed actors from CSV
    seed_actors = set()
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0].strip():
                    seed_actors.add(row[0].strip())
    except FileNotFoundError:
        return Response({"error": f"actors.csv not found at {csv_path}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Filter graph actors that are in the seed list
    actors = [
        node for node in graph.nodes
        if getattr(node, "is_person", False) and
           graph.nodes[node].get("name") in seed_actors
    ]

    if len(actors) < 2:
        return Response(
            {"error": f"Not enough seed actors found in graph. Found {len(actors)} matching actors."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    start_node, end_node = random.sample(actors, 2)

    return Response({
        "start_id": start_node.id,
        "start_name": graph.nodes[start_node].get("name"),
        "end_id": end_node.id,
        "end_name": graph.nodes[end_node].get("name"),
        "max_steps": 5
    })

@api_view(['POST'])
def validate_chain(request):
    """
    Expects JSON body:
    {
      "chain": ["Actor Name 1", "Movie Title 1", "Actor Name 2", "Movie Title 2", "Actor Name 3", ...],
      "start_name": "Actor Name Start",
      "end_name": "Actor Name End",
      "start_id": "123456",   <-- NEW
      "end_id": "654321"      <-- NEW
    }
    """
    graph, ia = get_graph_and_ia()
    data = request.data

    chain = data.get("chain")
    start_name = data.get("start_name")
    end_name = data.get("end_name")
    start_id = data.get("start_id")
    end_id = data.get("end_id")

    if not chain or not isinstance(chain, list):
        return Response({"error": "Invalid or missing 'chain' field"}, status=status.HTTP_400_BAD_REQUEST)
    if not start_name or not end_name:
        return Response({"error": "Missing 'start_name' or 'end_name'"}, status=status.HTTP_400_BAD_REQUEST)
    if not start_id or not end_id:
        return Response({"error": "Missing 'start_id' or 'end_id'"}, status=status.HTTP_400_BAD_REQUEST)

    # Helper functions
    def get_person_ids(name):
        results = ia.search_person(name)
        return {str(p.getID()) for p in results}

    def get_movie_ids(title):
        results = ia.search_movie(title)
        return {str(m.getID()) for m in results if m.get("kind") == "movie"}

    game = GameGraphAndHTTP(int(start_id), int(end_id), graph, ia)

    # ✅ First step: force exact start_id
    if len(chain) >= 3:
        person0_name = chain[0]
        work_title = chain[1]
        person1_name = chain[2]

        # force person0 set to only start_id
        people0 = {str(start_id)}
        works = get_movie_ids(work_title)
        people1 = get_person_ids(person1_name)

        if not works or not people1:
            return Response({"valid": False, "reason": "Invalid movie or next actor on first step"})

        valid, msg = game.take_step(str(start_id), str(list(people1)[0]), str(list(works)[0]))
        if not valid:
            return Response({"valid": False, "reason": f"Step error: {msg}"})

    # Remaining steps
    for i in range(2, len(chain) - 2, 2):
        person0_name = chain[i]
        work_title = chain[i + 1]
        person1_name = chain[i + 2]

        people0 = get_person_ids(person0_name)
        works = get_movie_ids(work_title)
        people1 = get_person_ids(person1_name)

        if not people0 or not works or not people1:
            return Response({"valid": False, "reason": "One of the entries could not be matched in IMDb"})

        valid, msg = game.take_step(str(list(people0)[0]), str(list(people1)[0]), str(list(works)[0]))
        if not valid:
            return Response({"valid": False, "reason": f"Step error: {msg}"})

    # ✅ Final check: ensure target actor ID matches
    last_actor_ids = get_person_ids(chain[-1])
    if str(end_id) in last_actor_ids or chain[-1].strip().lower() == end_name.strip().lower():
        return Response({"valid": True, "reason": "You completed the chain successfully!"})
    else:
        return Response({"valid": False, "reason": "Chain does not end with the target actor"})
