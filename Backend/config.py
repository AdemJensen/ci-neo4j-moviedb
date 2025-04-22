import os
import logging
from py2neo import Graph, NodeMatcher


# Neo4j connection setup
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# TMDB API setup
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "535b98608031a939cdef34fb2a98ebc5")
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")

PORT = os.getenv("PORT",10000)

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD),name="neo4j")
matcher = NodeMatcher(graph)

# Set up logging
logging.basicConfig(filename='api_log.txt', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')