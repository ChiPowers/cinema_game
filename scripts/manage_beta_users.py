#!/usr/bin/env python3
"""Manage beta user access.

Usage:
  poetry run python scripts/manage_beta_users.py add email@example.com
  poetry run python scripts/manage_beta_users.py remove email@example.com
  poetry run python scripts/manage_beta_users.py list
"""
import sys

sys.path.insert(0, ".")

from cinema_game_backend.env import load_cinema_game_env

load_cinema_game_env()

from cinema_game_backend.database import init_db, add_beta_user, remove_beta_user, list_beta_users

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
