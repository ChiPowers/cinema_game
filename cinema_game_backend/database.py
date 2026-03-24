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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_game(game: dict):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO games (
            id, start_actor_name, start_actor_id,
            end_actor_name, end_actor_id, difficulty,
            known_solution, moves, current_actor_name,
            current_actor_id, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def update_game(game_id: str, moves: list, current_actor: dict, status: str):
    conn = get_db()
    conn.execute(
        """
        UPDATE games
        SET moves = ?, current_actor_name = ?, current_actor_id = ?,
            status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """,
        (
            json.dumps(moves),
            current_actor["name"],
            current_actor["id"],
            status,
            game_id,
        ),
    )
    conn.commit()
    conn.close()


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
        "created_at": row["created_at"],
    }
