import pickle
import numpy as np

from cinema.imdb_config import ia
from cinema.cinegraph.compute_curated_graph import Curator
from cinema import directories

with open(directories.data('professional.pkl'), 'rb') as f:
     g = pickle.load(f)
with open("/Users/chivonpowers/ai_eng_ds/artist-graph/data/actors.csv") as f:
    actor_names = [a.strip() for a in f]

with open("/Users/chivonpowers/ai_eng_ds/artist-graph/data/movies.csv") as f:
    movie_names = [m.strip() for m in f]

curator = Curator(g, ia, actor_names, movie_names)

r = np.random.RandomState(42)
game_2 = [curator.game_maker.make_game(2, r) for _ in range(10)]
for a, b in game_2:
    print(curator.plot_path(a, b))
