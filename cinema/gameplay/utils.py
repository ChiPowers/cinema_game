import csv
import os

SEED_ACTORS_PATH = os.path.join("data", "actors.csv")

def load_seed_actors():
    seed_actors = set()
    with open(SEED_ACTORS_PATH, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Assuming the CSV has actor names in first column
            seed_actors.add(row[0].strip())
    return seed_actors

SEED_ACTORS = load_seed_actors()
