from fastapi import Request
from art_graph.cinema_data_providers.tmdb.client import TMDbClient


def get_tmdb(request: Request) -> TMDbClient:
    return request.app.state.tmdb
