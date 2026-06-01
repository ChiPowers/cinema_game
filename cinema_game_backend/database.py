import sqlite3
import json
from .config import DB_PATH


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS beta_users (
            email TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            start_actor_name TEXT NOT NULL,
            start_actor_id INTEGER NOT NULL,
            end_actor_name TEXT NOT NULL,
            end_actor_id INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            known_solution TEXT NOT NULL,
            moves TEXT NOT NULL DEFAULT '[]',
            current_actor_name TEXT NOT NULL,
            current_actor_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_progress',
            strikes INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: add strikes column to existing databases
    try:
        conn.execute("ALTER TABLE games ADD COLUMN strikes INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()


def is_beta_user(email: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM beta_users WHERE email = ?", (email.lower(),)
    ).fetchone()
    conn.close()
    return row is not None


def add_beta_user(email: str):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO beta_users (email) VALUES (?)", (email.lower(),)
    )
    conn.commit()
    conn.close()


def remove_beta_user(email: str):
    conn = get_db()
    conn.execute("DELETE FROM beta_users WHERE email = ?", (email.lower(),))
    conn.commit()
    conn.close()


def list_beta_users() -> list[str]:
    conn = get_db()
    rows = conn.execute("SELECT email FROM beta_users ORDER BY created_at").fetchall()
    conn.close()
    return [row["email"] for row in rows]


def save_game(game: dict):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO games (
            id, start_actor_name, start_actor_id,
            end_actor_name, end_actor_id, difficulty,
            known_solution, moves, current_actor_name,
            current_actor_id, status, strikes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            game["id"],
            game["start_actor"]["name"],
            game["start_actor"]["id"],
            game["end_actor"]["name"],
            game["end_actor"]["id"],
            game["difficulty"],
            json.dumps(game["known_solution"]),
            json.dumps(game["moves"]),
            game["current_actor"]["name"],
            game["current_actor"]["id"],
            game["status"],
            game.get("strikes", 0),
        ),
    )
    conn.commit()
    conn.close()


def load_game(game_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_game(row)


def update_game(
    game_id: str, moves: list, current_actor: dict, status: str, strikes: int = 0
):
    conn = get_db()
    conn.execute(
        """
        UPDATE games
        SET moves = ?, current_actor_name = ?, current_actor_id = ?,
            status = ?, strikes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """,
        (
            json.dumps(moves),
            current_actor["name"],
            current_actor["id"],
            status,
            strikes,
            game_id,
        ),
    )
    conn.commit()
    conn.close()


def list_games(limit: int | None = None) -> list[dict]:
    conn = get_db()
    query = "SELECT * FROM games ORDER BY created_at DESC"
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [_row_to_game(row) for row in rows]


def _row_to_game(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "start_actor": {"name": row["start_actor_name"], "id": row["start_actor_id"]},
        "end_actor": {"name": row["end_actor_name"], "id": row["end_actor_id"]},
        "difficulty": row["difficulty"],
        "known_solution": json.loads(row["known_solution"]),
        "moves": json.loads(row["moves"]),
        "current_actor": {
            "name": row["current_actor_name"],
            "id": row["current_actor_id"],
        },
        "status": row["status"],
        "strikes": row["strikes"] if "strikes" in row.keys() else 0,
        "created_at": row["created_at"],
    }
