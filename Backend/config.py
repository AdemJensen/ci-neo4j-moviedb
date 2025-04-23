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

SILICONFLOW_SK = os.getenv("SILICONFLOW_SK", "")
# SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "THUDM/glm-4-9b-chat")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "THUDM/GLM-4-32B-0414")

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD),name="neo4j")
matcher = NodeMatcher(graph)

# Set up logging
# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler('api_log.txt')
console_handler = logging.StreamHandler()

# Set level for handlers
file_handler.setLevel(logging.INFO)
console_handler.setLevel(logging.INFO)

# Create a formatter and set it for both handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)