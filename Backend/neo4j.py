from py2neo import Node, Relationship
from config import *


def add_actor_to_neo4j(actor_data):
    actor_node = Node("Actor",
                      name=actor_data['name'],
                      date_of_birth=actor_data['date_of_birth'],
                      gender=actor_data['gender'],
                      date_of_death=actor_data['date_of_death'],
                      profile_path=actor_data['profile_path'])  # Add profile path to node
    graph.merge(actor_node, "Actor", "name")

    for movie in actor_data['filmography']:
        movie_node = Node("Movie", title=movie['title'], year=movie['year'])
        graph.merge(movie_node, "Movie", "title")

        acted_in = Relationship(actor_node, "ACTED_IN", movie_node)
        graph.merge(acted_in)

    logging.info(f"Actor added to Neo4j with filmography: {actor_data['name']}")
    return actor_data


def add_movie_to_neo4j(movie_data):
    # Create or merge movie node
    movie_node = Node("Movie", title=movie_data['title'], year=movie_data['year'])
    graph.merge(movie_node, "Movie", "title")

    for actor in movie_data["cast"]:
        actor_node = Node("Actor",
                          name=actor['name'],
                          date_of_birth=actor['date_of_birth'],
                          gender=actor['gender'],
                          date_of_death=actor['date_of_death'],
                          profile_path=actor['profile_path'])  # Add profile path to node
        graph.merge(actor_node, "Actor", "name")

        acted_in = Relationship(actor_node, "ACTED_IN", movie_node)
        graph.merge(acted_in)

    logging.info(f"Movie added to Neo4j with cast: {movie_data['title']}")
    return movie_data