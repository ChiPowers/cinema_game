#!/usr/bin/env python3
"""Manage beta user access.

Usage:
  poetry run python scripts/manage_beta_users.py add email@example.com
  poetry run python scripts/manage_beta_users.py remove email@example.com
  poetry run python scripts/manage_beta_users.py list
"""

import sys

from cinema_game_backend.config import BETA_SEED_EMAILS
from cinema_game_backend.database import (
    init_db,
    add_beta_user,
    remove_beta_user,
    list_beta_users,
)

init_db()

command = sys.argv[1] if len(sys.argv) > 1 else "list"

if command == "add":
    if len(sys.argv) < 3:
        print("Usage: manage_beta_users.py add <email>")
        sys.exit(1)
    email = sys.argv[2]
    add_beta_user(email)
    print(f"Added: {email}")

elif command == "remove":
    if len(sys.argv) < 3:
        print("Usage: manage_beta_users.py remove <email>")
        sys.exit(1)
    email = sys.argv[2]
    remove_beta_user(email)
    print(f"Removed: {email}")
    seeded = {seed.strip().lower() for seed in BETA_SEED_EMAILS}
    if email.strip().lower() in seeded:
        print(
            f"WARNING: {email} is still listed in BETA_SEED_EMAILS "
            "(secrets/.env). It will be re-added automatically the next "
            "time the app starts. Remove it from BETA_SEED_EMAILS too if "
            "this removal should stick."
        )

elif command == "list":
    users = list_beta_users()
    if users:
        print(f"{len(users)} beta user(s):")
        for u in users:
            print(f"  {u}")
    else:
        print("No beta users.")

else:
    print(f"Unknown command: {command}")
    print("Commands: add, remove, list")
    sys.exit(1)
