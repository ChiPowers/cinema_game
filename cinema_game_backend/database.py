import json
import threading
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import URL, Connection, Row

from .config import DATABASE_URL, DB_PATH

metadata = MetaData()

beta_users = Table(
    "beta_users",
    metadata,
    Column("email", Text, primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

games = Table(
    "games",
    metadata,
    Column("id", Text, primary_key=True),
    Column("start_actor_name", Text, nullable=False),
    Column("start_actor_id", Integer, nullable=False),
    Column("end_actor_name", Text, nullable=False),
    Column("end_actor_id", Integer, nullable=False),
    Column("difficulty", Text, nullable=False),
    Column("known_solution", Text, nullable=False),
    Column("moves", Text, nullable=False, server_default="[]"),
    Column("current_actor_name", Text, nullable=False),
    Column("current_actor_id", Integer, nullable=False),
    Column("status", String, nullable=False, server_default="in_progress"),
    Column("strikes", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)

# Arbitrary constant identifying init_db's advisory lock (Postgres only).
_INIT_LOCK_KEY = 0x63696E656D61  # "cinema"

_engine: Engine | None = None
_engine_lock = threading.Lock()


def _normalise_url(url: str) -> str:
    # Hosts hand out bare postgres:// or postgresql:// URLs; SQLAlchemy would
    # resolve those to psycopg2. Pin the psycopg (v3) driver we depend on.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def _app_database_url() -> str | URL:
    if DATABASE_URL:
        return _normalise_url(DATABASE_URL)
    # URL.create keeps DB_PATH verbatim; "sqlite:///" + DB_PATH would truncate
    # a path containing "?" at that character.
    return URL.create("sqlite", database=DB_PATH)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_engine(_app_database_url(), pool_pre_ping=True)
    return _engine


def set_engine(engine: Engine | None) -> None:
    """Replace the process-wide engine (tests); None resets to lazy creation."""
    global _engine
    _engine = engine


def _insert_ignore(conn: Connection, table: Table, values: dict):
    """INSERT ... ON CONFLICT DO NOTHING on either supported dialect."""
    dialect = conn.dialect.name
    if dialect == "postgresql":
        return postgresql.insert(table).values(values).on_conflict_do_nothing()
    if dialect == "sqlite":
        return sqlite.insert(table).values(values).on_conflict_do_nothing()
    raise NotImplementedError(f"Unsupported database dialect: {dialect}")


def init_db(engine: Engine | None = None):
    """Create tables and apply migrations. Safe to run concurrently.

    CREATE TABLE IF NOT EXISTS is NOT race-safe on Postgres: two sessions can
    both pass the existence check and one then fails with a unique violation on
    pg_type. Overlapping Cloud Run instances run this at startup, so on Postgres
    the whole routine is serialised with a transaction-scoped advisory lock
    (released automatically at commit/rollback, even if the instance dies).
    SQLite serialises writers itself.
    """
    with (engine or get_engine()).begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": _INIT_LOCK_KEY}
            )
        metadata.create_all(conn, checkfirst=True)
        _add_missing_columns(conn)


def _add_missing_columns(conn: Connection) -> None:
    # Migration: add strikes column to databases created before it existed.
    # Inspected rather than try/except: a failed ALTER aborts a Postgres
    # transaction, so swallowing the error would break everything after it.
    columns = {c["name"] for c in inspect(conn).get_columns("games")}
    if "strikes" not in columns:
        conn.execute(
            text("ALTER TABLE games ADD COLUMN strikes INTEGER NOT NULL DEFAULT 0")
        )


def is_beta_user(email: str) -> bool:
    with get_engine().connect() as conn:
        row = conn.execute(
            select(beta_users.c.email).where(beta_users.c.email == email.lower())
        ).first()
    return row is not None


def add_beta_user(email: str):
    with get_engine().begin() as conn:
        conn.execute(_insert_ignore(conn, beta_users, {"email": email.lower()}))


def seed_beta_users(emails: list[str]):
    for email in emails:
        add_beta_user(email)


def remove_beta_user(email: str):
    with get_engine().begin() as conn:
        conn.execute(delete(beta_users).where(beta_users.c.email == email.lower()))


def list_beta_users() -> list[str]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(beta_users.c.email).order_by(
                beta_users.c.created_at, beta_users.c.email
            )
        ).all()
    return [row.email for row in rows]


def save_game(game: dict):
    with get_engine().begin() as conn:
        conn.execute(
            insert(games).values(
                id=game["id"],
                start_actor_name=game["start_actor"]["name"],
                start_actor_id=game["start_actor"]["id"],
                end_actor_name=game["end_actor"]["name"],
                end_actor_id=game["end_actor"]["id"],
                difficulty=game["difficulty"],
                known_solution=json.dumps(game["known_solution"]),
                moves=json.dumps(game["moves"]),
                current_actor_name=game["current_actor"]["name"],
                current_actor_id=game["current_actor"]["id"],
                status=game["status"],
                strikes=game.get("strikes", 0),
            )
        )


def load_game(game_id: str) -> dict | None:
    with get_engine().connect() as conn:
        row = conn.execute(select(games).where(games.c.id == game_id)).first()
    if row is None:
        return None
    return _row_to_game(row)


def update_game(
    game_id: str, moves: list, current_actor: dict, status: str, strikes: int = 0
):
    with get_engine().begin() as conn:
        conn.execute(
            update(games)
            .where(games.c.id == game_id)
            .values(
                moves=json.dumps(moves),
                current_actor_name=current_actor["name"],
                current_actor_id=current_actor["id"],
                status=status,
                strikes=strikes,
                updated_at=func.now(),
            )
        )


def list_games(limit: int | None = None) -> list[dict]:
    query = select(games).order_by(games.c.created_at.desc(), games.c.id)
    if limit is not None:
        query = query.limit(int(limit))
    with get_engine().connect() as conn:
        rows = conn.execute(query).all()
    return [_row_to_game(row) for row in rows]


def _format_timestamp(value: datetime | None) -> str | None:
    # The API exposes created_at as a string (GameState.created_at). Normalise
    # both dialects to the fixed-width UTC "YYYY-MM-DD HH:MM:SS" SQLite always
    # produced: Postgres returns tz-aware values with microseconds.
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat(sep=" ")


def _row_to_game(row: Row) -> dict:
    return {
        "id": row.id,
        "start_actor": {"name": row.start_actor_name, "id": row.start_actor_id},
        "end_actor": {"name": row.end_actor_name, "id": row.end_actor_id},
        "difficulty": row.difficulty,
        "known_solution": json.loads(row.known_solution),
        "moves": json.loads(row.moves),
        "current_actor": {
            "name": row.current_actor_name,
            "id": row.current_actor_id,
        },
        "status": row.status,
        "strikes": row.strikes,
        "created_at": _format_timestamp(row.created_at),
    }
