# Cinema Game
Cinema Game is not a commercial product and has never been deployed to production. It began as a limited experiment to 
measure how humans could understand a profession network graph. Try to answer the following question. What is the 
shortest path between Brad Pitt and Colin Firth? Consider two actors to be connected and if they have appeared in the 
same movie and two movies to be connected if at least one appeared in both. There is a path which connects these two 
actors.

If two actors have appeared in the same movie, then they are considered directly connected, with a path of length 1. 
The distance between two actors can only decrease, but at the time we first asked this question, there was a path 
of length 2 between Brad Pitt and Colin Firth. Brad Pitt and Michael Fassbender were both in 12 Years a Slave. Michael 
Fassbender and Nicholas Hoult were both in X-Men: Apocalypse. Nicholas Hoult and Colin Firth were both in A Single Man.  

The code here is capable of building a professional graph from the database which IMDb has courteously provided for 
educators and researchers. With small modification, it can also produce a graph from similar databases such as citation 
data for scholarly research papers or musical discographies.

For now, we have performed some small experiments, but already there are some intriguing results. Please, give this a 
try. Compute the PageRank for various subsets of the movie and television professional graph. Try reweighting the edges 
to see how the results change.

For some of us, playing this kind of game is actually much more fun than watching the movies themselves.

## To begin
Install dependencies from `requirements.txt`. With Anaconda create an environment by

    conda create -n cinema python=3.10
    conda activate cinema 
    pip install -e .
    ./manage.py migrate

That much will set up the Django project. Downloading data and constructing a professional graph will probably require 
about 16GB RAM.

    ./manage.py runscript make_imdb_professional_graph

That will create a pickle file of a networkx graph called `data/professional.pkl`. That graph is a bipartite graph whose
vertices are people and movies. People are connected to movies and movies are connected to people (hence, bipartite).
The edges are movie credits, that is an edge exists between a person and a movie if that person appeared in the credits
for that movie. In this case, we consider only edges which correspond to contributing to a movie as an actor, actress, 
writer, director or producer. The professional graph is the connected component which contains Fred Astaire.

## PageRank experiments
To compute the PageRank of the professional graph computed earlier

    ./manage.py runscript page_rank
