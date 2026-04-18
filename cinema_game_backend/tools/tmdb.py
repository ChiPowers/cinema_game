from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from art_graph.cinema_data_providers.tmdb.config import TMDbConfig
from ..config import TMDB_API_KEY, TMDB_IMAGE_BASE, TMDB_BACKDROP_BASE

tmdb = TMDbClient(TMDbConfig(
    api_key=TMDB_API_KEY,
    image_base=TMDB_IMAGE_BASE,
    backdrop_base=TMDB_BACKDROP_BASE,
))
