# scripts/make_imdb_professional_graph.py
# Internet Movie Database Inc. makes publicly available a limited dataset for academic purposes.
# See https://www.imdb.com/interfaces/
# Carefully check license to make sure this is matches you intended use.

import os
from tqdm import tqdm
import requests
import networkx as nx
import pickle

from cinema import directories
from cinema.cinegraph import imdb_tsv
from cinema.cinegraph.grapher import PersonNode


def retrieve_imdb_data(filename):
    path = directories.data(filename)
    print(path)
    if os.path.exists(path):
        print("{} already exists".format(path))
        return
    url = "https://datasets.imdbws.com/{}".format(filename)
    print("Down loading {}".format(url))
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
    with open(path, "wb") as f:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()


def filtered_graph_update(g, df, row_update, predicate=None):
    if predicate is None:
        predicate = lambda row: True
    with tqdm(total=len(df)) as pbar:
        for _, row in df.iterrows():
            if predicate(row):
                row_update(g, row)
            pbar.update(1)


def populate_people(g):
    relevant = set("actor,actress,writer,director,producer".split(","))

    def predicate(row):
        primary_professions = row["primaryProfession"]
        try:
            professions = set(primary_professions.split(","))
        except:
            return False
        return not relevant.isdisjoint(professions)

    print("loading people data")
    df = imdb_tsv.load_names()
    print("data loaded")
    filtered_graph_update(g, df, imdb_tsv.add_person, predicate=predicate)


def populate_movies(g):
    print("loading work data")
    df = imdb_tsv.load_basics()
    print("data loaded")
    predicate = lambda row: row["titleType"] == "movie"
    filtered_graph_update(g, df, imdb_tsv.add_work, predicate=predicate)


def update_ratings(g):
    print("loading rating data")
    df = imdb_tsv.load_ratings()
    print("data loaded")
    filtered_graph_update(g, df, imdb_tsv.update_rating)


def make_edges(g):
    print("loading credits data")
    df = imdb_tsv.load_principals()
    print("data loaded")
    relevant_jobs = "actor,actress,writer,director,producer".split(",")
    predicate = lambda row: row["category"] in relevant_jobs
    filtered_graph_update(g, df, imdb_tsv.add_contribution, predicate=predicate)


def make_professional_graph():
    g = nx.Graph()
    populate_people(g)
    populate_movies(g)
    update_ratings(g)
    make_edges(g)
    # we want the component with Fred Astaire who has ID 1
    return g.subgraph(nx.node_connected_component(g, PersonNode(1))).copy()


def run():
    print("Downloading data")
    retrieve_imdb_data("name.basics.tsv.gz")
    retrieve_imdb_data("title.basics.tsv.gz")
    retrieve_imdb_data("title.ratings.tsv.gz")
    retrieve_imdb_data("title.principals.tsv.gz")

    print("Creating graph")
    g = make_professional_graph()
    with open(directories.data("professional.pkl"), "wb") as f:
        pickle.dump(g, f)
