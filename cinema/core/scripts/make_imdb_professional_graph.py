# scripts/make_imdb_professional_graph.py
# Internet Movie Database Inc. makes publicly available a limited dataset for academic purposes.
# See https://www.imdb.com/interfaces/
# Carefully check license to make sure this is matches you intended use.

import os
from tqdm import tqdm
import requests

from cinema import directories


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


def run():
    print("hi")
    retrieve_imdb_data("name.basics.tsv.gz")
    retrieve_imdb_data("title.basics.tsv.gz")
    retrieve_imdb_data("title.ratings.tsv.gz")
    retrieve_imdb_data("title.principals.tsv.gz")
