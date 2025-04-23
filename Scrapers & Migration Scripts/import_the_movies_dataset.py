import csv
import ast
from py2neo import Graph, Node, Relationship
from tqdm import tqdm

# Connect to Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

# File paths
MOVIE_METADATA_CSV = "../Backend/recommendation/TheMoviesDataset/movies_metadata.csv"
CREDITS_CSV = "../Backend/recommendation/TheMoviesDataset/credits.csv"

# Load credits into a dictionary keyed by movie ID
credits_map = {}

with open(CREDITS_CSV, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        movie_id = row['id']
        try:
            cast = ast.literal_eval(row['cast'])
            credits_map[movie_id] = cast
        except Exception as e:
            print(f"Error parsing cast for movie ID {movie_id}: {e}")

# Read all movie rows first (so tqdm can show total)
with open(MOVIE_METADATA_CSV, encoding='utf-8') as f:
    reader = list(csv.DictReader(f))  # Convert to list for length

# BATCH_SIZE = 1000
# tx = graph.begin()
# batch_count = 0

# Import movies and cast with progress bar
for row in tqdm(reader, desc="Importing movies", unit="movies"):
    movie_id = row['id']
    title = row.get('title')
    release_date = row.get('release_date')

    if not movie_id.isdigit() or not title:
        continue

    year = release_date[:4] if release_date and len(release_date) >= 4 else "Unknown"
    movie_node = Node("Movie", title=title.strip(), year=year)
    graph.merge(movie_node, "Movie", "title")

    cast_list = credits_map.get(movie_id, [])
    for actor in cast_list:
        name = actor.get("name")
        profile_path = actor.get("profile_path")
        gender_map = {1: "Female", 2: "Male"}
        gender = gender_map.get(actor.get("gender"), None)

        if not name:
            continue

        actor_node = Node("Actor", name=name.strip(), gender=gender, profile_path=profile_path)
        graph.merge(actor_node, "Actor", "name")
        graph.merge(Relationship(actor_node, "ACTED_IN", movie_node))

    # batch_count += 1
    # if batch_count >= BATCH_SIZE:
    #     # Commit the transaction and start a new one
    #     print(tx, f"Committing batch of {batch_count} movies...")
    #     tx.commit()
    #     tx = graph.begin()
    #     batch_count = 0

print("Import completed.")
