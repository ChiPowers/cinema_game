import jwt
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from fastapi import Header, HTTPException, Request

from .config import NEXTAUTH_SECRET, create_llm_provider


def get_tmdb(request: Request) -> TMDbClient:
    return request.app.state.tmdb


def get_llm(request: Request):
    """Return the LLM provider, constructing it on first use.

    The lifespan has already validated the configuration and confirmed the
    backend module is present (via find_spec, which locates without
    importing). That rules out the reasons a healthy container could have
    caught at startup -- failure here is limited to problems only an actual
    import can reveal, such as a broken transitive install.
    """
    if request.app.state.llm is None:
        request.app.state.llm = create_llm_provider()
    return request.app.state.llm


async def require_auth(authorization: str = Header(...)) -> dict:
    if not NEXTAUTH_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, NEXTAUTH_SECRET, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
