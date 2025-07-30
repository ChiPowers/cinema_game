import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

st.title("🎬 Cinema Connection Game")

# --- Start a new game ---
if "game_data" not in st.session_state:
    resp = requests.get(f"{BASE_URL}/start/").json()
    st.session_state.game_data = resp
    st.session_state.chain = [resp["start_name"]]  # start actor prefilled

start_actor = st.session_state.game_data["start_name"]
end_actor = st.session_state.game_data["end_name"]

st.write(f"**Start Actor:** {start_actor}")
st.write(f"**End Actor:** {end_actor}")

# --- Show current chain ---
st.write("Your chain so far:")
st.write(" → ".join(st.session_state.chain))

# --- Add next step ---
if len(st.session_state.chain) % 2 == 1:
    # expecting movie
    movie = st.text_input("🎥 was in this movie:", key=f"movie_{len(st.session_state.chain)}")
    if movie and st.button("Add movie"):
        st.session_state.chain.append(movie)
else:
    # expecting actor
    actor = st.text_input("⭐ with this actor:", key=f"actor_{len(st.session_state.chain)}")
    if actor and st.button("Add actor"):
        st.session_state.chain.append(actor)

# --- Submit chain for validation ---
if st.session_state.chain[-1].lower() == end_actor.lower():
    if st.button("✅ Submit chain"):
        payload = {
            "chain": st.session_state.chain,
            "start_name": start_actor,
            "end_name": end_actor,
            "start_id": st.session_state.game_data["start_id"],
            "end_id": st.session_state.game_data["end_id"],
        }
        resp = requests.post(f"{BASE_URL}/validate/", json=payload).json()
        st.write("### Server Response:")
        st.write(resp)
