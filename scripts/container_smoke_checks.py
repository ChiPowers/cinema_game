"""Checks run inside the backend container by container_smoke.sh.

Piped to the container's own interpreter (`docker exec -i <c> python -`), so
it may use only the standard library and the installed app package. Exits
non-zero on the first failed check.

Usage: container_smoke_checks.py <scenario>
"""

import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
SEED_EMAIL = "seed@example.com"
INTERNAL_SECRET = "smoke-secret"
LEGACY_GAME_ID = "legacy-game"


def wait_for_health(timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=3) as res:
                return json.load(res)
        except (urllib.error.URLError, ConnectionError):
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


def check_beta(email: str) -> int:
    req = urllib.request.Request(
        f"{BASE}/auth/check-beta",
        data=json.dumps({"email": email}).encode(),
        headers={
            "content-type": "application/json",
            "x-internal-secret": INTERNAL_SECRET,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status
    except urllib.error.HTTPError as e:
        return e.code


def check(label: str, ok: bool, detail: object = "") -> None:
    if ok:
        print(f"ok   {label}")
    else:
        print(f"FAIL {label} {detail}".rstrip())
        sys.exit(1)


def main(scenario: str) -> None:
    check("/health", wait_for_health() == {"status": "ok"})
    check("seeded email is allowed", check_beta(SEED_EMAIL) == 200)
    check("unknown email is refused", check_beta("nobody@example.com") == 403)

    # Imported only after /health answers, so the app has already run init_db.
    from cinema_game_backend import database
    from cinema_game_backend.config import DB_PATH

    # Read the schema directly: load_game reports 0 strikes for a row with no
    # strikes column, so it cannot tell whether the migration actually ran.
    with sqlite3.connect(DB_PATH) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(games)")}
    check("games has strikes column", "strikes" in columns)

    if scenario == "legacy":
        game = database.load_game(LEGACY_GAME_ID)
        check("pre-strikes game still loads", game is not None)
        check("pre-strikes game has 0 strikes", game["strikes"] == 0, game["strikes"])

    database.save_game(
        {
            "id": "smoke-game",
            "start_actor": {"name": "A", "id": 1},
            "end_actor": {"name": "B", "id": 2},
            "difficulty": "easy",
            "known_solution": [],
            "moves": [],
            "current_actor": {"name": "A", "id": 1},
            "status": "in_progress",
        }
    )
    move = {"type": "movie", "title": "M", "id": 9}
    database.update_game("smoke-game", [move], {"name": "C", "id": 3}, "in_progress", 1)
    game = database.load_game("smoke-game")
    check(
        "save, update, load round trip",
        game["moves"] == [move]
        and game["current_actor"]["id"] == 3
        and game["strikes"] == 1,
        game,
    )


if __name__ == "__main__":
    main(sys.argv[1])
