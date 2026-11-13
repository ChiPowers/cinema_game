#!/usr/bin/env bash
# Smoke-test a built backend image the way docker-compose runs it: a named
# volume at /data, the SQLite database on it, and the app started by the
# image's own CMD. Unit tests never build or run the image, so this is the
# only check that the Dockerfile, the /data volume, the strikes migration
# and beta-user seeding still work together.
#
# Scenarios:
#   empty   a fresh volume; the app must create its tables
#   legacy  a database from before the strikes column; the app must migrate
#           it on startup and still load the game already in it
#
# Usage: scripts/container_smoke.sh <image>
# Example:
#   docker build --build-arg LLM_EXTRA=anthropic -t cinema-backend:smoke .
#   scripts/container_smoke.sh cinema-backend:smoke
set -euo pipefail

IMAGE=${1:?usage: container_smoke.sh <image>}
CHECKS="$(cd "$(dirname "$0")" && pwd)/container_smoke_checks.py"
PREFIX="cinema-smoke-$$"

cleanup() {
  docker rm -f "$PREFIX-empty" "$PREFIX-legacy" >/dev/null 2>&1 || true
  docker volume rm "$PREFIX-empty" "$PREFIX-legacy" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# The schema as it was before strikes was added, with one game in it.
LEGACY_SQL="
CREATE TABLE beta_users (
    email TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE games (
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
);
INSERT INTO games (id, start_actor_name, start_actor_id, end_actor_name,
    end_actor_id, difficulty, known_solution, current_actor_name,
    current_actor_id)
VALUES ('legacy-game', 'A', 1, 'B', 2, 'easy', '[]', 'A', 1);
"

run_scenario() {
  local scenario=$1 name="$PREFIX-$1"
  echo "== $scenario"
  docker volume create "$name" >/dev/null

  if [ "$scenario" = legacy ]; then
    # Written by the image's own interpreter as the image's user, so the file
    # has the ownership a real volume would.
    docker run --rm -v "$name:/data" --entrypoint python "$IMAGE" -c \
      "import sqlite3, sys; sqlite3.connect('/data/cinema_game.db').executescript(sys.argv[1])" \
      "$LEGACY_SQL"
  fi

  # Placeholder credentials: startup only checks that the selected provider's
  # variables are set, and no check here reaches TMDb or an LLM.
  docker run -d --name "$name" -v "$name:/data" \
    -e NEXTAUTH_SECRET=smoke -e INTERNAL_SECRET=smoke-secret \
    -e BETA_SEED_EMAILS=seed@example.com -e TMDB_API_KEY=smoke \
    -e ANTHROPIC_API_KEY=smoke -e OPENAI_API_KEY=smoke \
    -e VERTEX_PROJECT_ID=smoke -e VERTEX_LOCATION=smoke \
    "$IMAGE" >/dev/null

  local status=0
  docker exec -i "$name" python - "$scenario" <"$CHECKS" || status=$?
  if [ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]; then
    echo "FAIL container exited"
    status=1
  fi
  if docker logs "$name" 2>&1 | grep -q Traceback; then
    echo "FAIL traceback in container log"
    status=1
  fi
  if [ "$status" -ne 0 ]; then
    echo "-- container log ($scenario)"
    docker logs "$name" 2>&1 | tail -50
    return "$status"
  fi
}

run_scenario empty
run_scenario legacy
echo "container smoke test passed"
