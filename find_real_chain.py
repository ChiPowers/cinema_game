import pickle
import requests
import networkx as nx

BASE_URL = "http://127.0.0.1:8000"
PICKLE_PATH = "data/professional.pkl"  # adjust if needed

def load_graph():
    print("📂 Loading professional graph...")
    with open(PICKLE_PATH, "rb") as f:
        g = pickle.load(f)
    return g

def find_chain(g, start_id, end_id):
    """
    Returns a chain in the format:
    [actor_name, movie_title, actor_name, movie_title, ..., actor_name]
    """
    from cinema.cinegraph.node_types import PersonNode, WorkNode

    start_node = PersonNode(int(start_id))
    end_node = PersonNode(int(end_id))

    try:
        path = nx.shortest_path(g, start_node, end_node)
    except nx.NetworkXNoPath:
        print("❌ No path found between these actors.")
        return None

    chain = []
    for node in path:
        if node.is_person:
            person_name = g.nodes[node].get("name", f"Person {node.id}")
            chain.append(person_name)
        else:
            movie_name = g.nodes[node].get("title", f"Movie {node.id}")
            chain.append(movie_name)

    return chain

def test_valid_chain(chain, start_actor, end_actor):
    print("\n📡 Sending chain to validate...")
    payload = {
        "chain": chain,
        "start_name": start_actor,
        "end_name": end_actor
    }
    response = requests.post(f"{BASE_URL}/validate/", json=payload)
    try:
        print("Server Response:", response.json())
    except requests.exceptions.JSONDecodeError:
        print("❌ Error: Server returned invalid JSON response.")

if __name__ == "__main__":
    # 1️⃣ Load the game from API
    print("🎬 Starting a new game...")
    game_resp = requests.get(f"{BASE_URL}/start/")
    game = game_resp.json()
    print("Start Actor:", game["start_name"])
    print("End Actor:", game["end_name"])

    # 2️⃣ Load the professional graph
    g = load_graph()

    # 3️⃣ Find a valid chain
    chain = find_chain(g, game["start_id"], game["end_id"])
    if chain:
        print("✅ Found a valid chain:", " -> ".join(chain))
        # 4️⃣ Test it with the validate API using ACTOR NAMES
        test_valid_chain(chain, game["start_name"], game["end_name"])
    else:
        print("⚠️ No valid chain found for this random actor pair.")
