"""A slow database call must not stall other requests.

The route handlers are `async def`, so anything they call synchronously runs
on the event loop and blocks every other request served by that worker,
including /health, which the container healthcheck uses. The database layer
is synchronous, so the handlers must run its calls in a worker thread.

Each test makes one database call artificially slow (0.5 s), starts a request
that hits it, waits until that call has actually begun, and then times
/health. Blocked, /health waits about 0.5 s. Free, it answers in a few ms.

NOT RUN IN CI, ON PURPOSE. These are timing tests. They depend on thread
scheduling and wall-clock time, so a pass shows only that the stall did not
happen on this run, not that it cannot happen. A test like this could pass in
CI while the bug remains, and could fail on a slow runner when it does not.

Agents and developers: run these periodically, and always after changing the
route handlers in cinema_game_backend/routes/ or the database layer in
cinema_game_backend/database.py:

    conda run -n cinema-fastapi poetry run pytest functional_tests/concurrency/

They need no credentials and no network.
"""

import asyncio
import time

import httpx

from cinema_game_backend.main import app
from cinema_game_backend.routes import auth as auth_routes
from cinema_game_backend.routes import game as game_routes

SLOW_CALL = 0.5
# Far below SLOW_CALL, so a blocked loop always fails; far above a free
# request's few milliseconds, so scheduling noise does not.
STALL_LIMIT = 0.2


def _slow_down(monkeypatch, module, name: str) -> list:
    """Make module.name sleep before running; return a list it appends to."""
    started = []
    real = getattr(module, name)

    def slow(*args, **kwargs):
        started.append(True)
        time.sleep(SLOW_CALL)
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, slow)
    return started


async def _health_time_while(send, started: list) -> float:
    """Send a request, wait until its slow DB call begins, then time /health."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        t0 = time.perf_counter()
        pending = asyncio.create_task(send(c))
        # If the slow call runs on the loop, this loop cannot resume until it
        # finishes, and that time shows up in the /health measurement.
        while not started:
            await asyncio.sleep(0.001)
        await c.get("/health")
        elapsed = time.perf_counter() - t0
        await pending
    return elapsed


async def test_get_game_does_not_stall_the_event_loop(monkeypatch, game_id):
    started = _slow_down(monkeypatch, game_routes, "load_game")

    elapsed = await _health_time_while(lambda c: c.get(f"/game/{game_id}"), started)

    assert elapsed < STALL_LIMIT, f"/health waited {elapsed:.3f}s"


async def test_check_beta_does_not_stall_the_event_loop(monkeypatch):
    monkeypatch.setattr(auth_routes, "INTERNAL_SECRET", "secret")
    started = _slow_down(monkeypatch, auth_routes, "is_beta_user")

    def send(c):
        return c.post(
            "/auth/check-beta",
            json={"email": "nobody@example.com"},
            headers={"x-internal-secret": "secret"},
        )

    elapsed = await _health_time_while(send, started)

    assert elapsed < STALL_LIMIT, f"/health waited {elapsed:.3f}s"
