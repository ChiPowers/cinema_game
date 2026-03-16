"""
Tool definitions passed to Claude for agentic move validation.
Custom TMDb tools + Claude's built-in web_search tool.
"""

TMDB_TOOLS = [
    {
        "name": "search_actor",
        "description": (
            "Search for an actor or actress by name on TMDb. "
            "Returns their TMDb ID, full name, popularity score, and known-for movies. "
            "Use this to resolve an actor name to a TMDb ID before calling other tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name of the actor to search for"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_movie",
        "description": (
            "Search for a movie by title on TMDb. "
            "Returns the TMDb movie ID, exact title, release year, poster URL, and backdrop URL. "
            "Use this to resolve a movie title to a TMDb ID before fetching its cast."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the movie"},
                "year": {"type": "integer", "description": "Optional release year to narrow results"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "get_movie_cast",
        "description": (
            "Get the full cast list for a movie using its TMDb ID. "
            "Returns actor names, IDs, characters played, and billing order. "
            "Use this to check whether specific actors appear in a movie."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "movie_id": {"type": "integer", "description": "TMDb movie ID"},
            },
            "required": ["movie_id"],
        },
    },
]

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}

ALL_TOOLS = TMDB_TOOLS + [WEB_SEARCH_TOOL]
