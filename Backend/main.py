import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from py2neo import Graph, Node, Relationship, NodeMatcher
from typing import Optional, List
import logging
import requests
import re
import httpx
from datetime import datetime
import asyncio
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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

# Load HTML content
# Update the HTML content loading to use a function
def get_html_content():
    print("Loading HTML content")
    logging.info("Loading HTML content")
    html_path = Path(__file__).parent / "index.html"
    print(f"HTML path: {html_path}")
    try:
        with open(html_path, "r", encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f"index.html not found at {html_path}")
        return "Error: index.html not found"
    except Exception as e:
        logging.error(f"Error reading index.html: {str(e)}")
        return f"Error reading index.html: {str(e)}"

logging.basicConfig(
    filename=Path(__file__).parent.parent / 'api_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
    
@app.get("/autocomplete/{search_type}")
async def autocomplete(search_type: str, query: str = Query(..., min_length=1)):
    if search_type not in ['actor', 'movie']:
        raise HTTPException(status_code=400, detail="Invalid search type")
    
    # Define label based on search type
    label = 'Actor' if search_type == 'actor' else 'Movie'
    property_name = 'name' if search_type == 'actor' else 'title'
    
    # Modified Cypher query to handle both exact and partial matches
    cypher_query = f"""
    MATCH (n:{label})
    WHERE toLower(n.{property_name}) CONTAINS toLower($query)
    WITH n, 
         CASE WHEN toLower(n.{property_name}) = toLower($query) THEN 0
              WHEN toLower(n.{property_name}) STARTS WITH toLower($query) THEN 1
              ELSE 2 END as relevance
    ORDER BY relevance, n.{property_name}
    RETURN n.{property_name} AS name, relevance
    LIMIT 10
    """
    
    try:
        results = graph.run(cypher_query, query=query).data()
        
        # Format results
        suggestions = [result['name'] for result in results]
        return suggestions
        
    except Exception as e:
        logging.error(f"Error in autocomplete: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/search/{search_type}")
async def search(search_type: str, query: str = Query(..., min_length=1)):
    if search_type not in ['actor', 'movie']:
        raise HTTPException(status_code=400, detail="Invalid search type")
    
    label = 'Actor' if search_type == 'actor' else 'Movie'
    property_name = 'name' if search_type == 'actor' else 'title'
    
    cypher_query = f"""
    MATCH (n:{label})
    WHERE toLower(n.{property_name}) CONTAINS toLower($query)
    WITH n,
         CASE WHEN toLower(n.{property_name}) = toLower($query) THEN 0
              WHEN toLower(n.{property_name}) STARTS WITH toLower($query) THEN 1
              ELSE 2 END as relevance
    ORDER BY relevance, n.{property_name}
    RETURN n
    LIMIT 20
    """
    
    try:
        results = graph.run(cypher_query, query=query).data()
        return [dict(result['n']) for result in results]
    except Exception as e:
        logging.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
class Actor(BaseModel):
    name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    date_of_death: Optional[str] = None
    profile_path: Optional[str] = None

class Movie(BaseModel):
    title: str
    year: str

class ActorInMovie(BaseModel):
    actor_name: str
    movie_title: str

class ActorFilmography(BaseModel):
    actor: Actor
    movies: List[Movie]

class ActorCreate(BaseModel):
    name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
# Actor CRUD operations
@app.post("/actors", response_model=Actor)
async def create_actor(actor: Actor):
    try:
        actor_node = Node("Actor", **actor.dict())
        graph.create(actor_node)
        logging.info(f"Actor created: {actor.name}")
        return actor
    except Exception as e:
        logging.error(f"Error creating actor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/actors/{name}", response_model=Actor)
async def read_actor(name: str):
    actor_node = matcher.match("Actor", name=name).first()
    if actor_node:
        return Actor(**dict(actor_node))
    raise HTTPException(status_code=404, detail="Actor not found")

@app.get("/actors", response_model=List[Actor])
async def read_actors(
    page: int = Query(1, ge=1),
    size: int = Query(33, ge=1, le=100),
):
    skip = (page - 1) * size
    actors = matcher.match("Actor").skip(skip).limit(size)
    return [Actor(**dict(actor)) for actor in actors]

@app.get("/actors_count")
async def count_actors():
    total = graph.evaluate("MATCH (a:Actor) RETURN count(a)")
    return {"total": total}

@app.delete("/actors/{name}")
async def delete_actor(name: str):
    actor_node = matcher.match("Actor", name=name).first()
    if actor_node:
        graph.delete(actor_node)
        logging.info(f"Actor deleted: {name}")
        return {"message": f"Actor {name} deleted successfully"}
    raise HTTPException(status_code=404, detail="Actor not found")

# Movie CRUD operations
@app.post("/movies", response_model=Movie)
async def create_movie(movie: Movie):
    try:
        movie_node = Node("Movie", **movie.dict())
        graph.create(movie_node)
        logging.info(f"Movie created: {movie.title}")
        return movie
    except Exception as e:
        logging.error(f"Error creating movie: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/{title}", response_model=Movie)
async def read_movie(title: str):
    movie_node = matcher.match("Movie", title=title).first()
    if movie_node:
        return Movie(**dict(movie_node))
    raise HTTPException(status_code=404, detail="Movie not found")

@app.get("/movies", response_model=List[Movie])
async def read_movies(
    page: int = Query(1, ge=1),
    size: int = Query(33, ge=1, le=100),
):
    skip = (page - 1) * size
    movies = matcher.match("Movie").skip(skip).limit(size)

    return [Movie(**dict(movie)) for movie in movies]

@app.get("/movies_count")
async def count_movies():
    total = graph.evaluate("MATCH (m:Movie) RETURN count(m)")
    return {"total": total}

@app.put("/movies/{title}", response_model=Movie)
async def update_movie(title: str, movie: Movie):
    movie_node = matcher.match("Movie", title=title).first()
    if movie_node:
        movie_node.update(**movie.dict())
        graph.push(movie_node)
        logging.info(f"Movie updated: {title}")
        return Movie(**dict(movie_node))
    raise HTTPException(status_code=404, detail="Movie not found")

@app.delete("/movies/{title}")
async def delete_movie(title: str):
    movie_node = matcher.match("Movie", title=title).first()
    if movie_node:
        graph.delete(movie_node)
        logging.info(f"Movie deleted: {title}")
        return {"message": f"Movie {title} deleted successfully"}
    raise HTTPException(status_code=404, detail="Movie not found")

# Relationship operation
@app.post("/actor_in_movie")
async def add_actor_to_movie(relation: ActorInMovie):
    try:
        actor_node = matcher.match("Actor", name=relation.actor_name).first()
        movie_node = matcher.match("Movie", title=relation.movie_title).first()
        
        if not actor_node:
            raise HTTPException(status_code=404, detail="Actor not found")
        if not movie_node:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        acted_in = Relationship(actor_node, "ACTED_IN", movie_node)
        graph.merge(acted_in)
        
        logging.info(f"Relationship added: {relation.actor_name} ACTED_IN {relation.movie_title}")
        return {"message": f"Relationship added: {relation.actor_name} ACTED_IN {relation.movie_title}"}
    except Exception as e:
        logging.error(f"Error adding relationship: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# TMDB Integration
def fetch_actor_from_tmdb(actor_name):
    search_url = f"{TMDB_BASE_URL}/search/person"
    params = {
        "api_key": TMDB_API_KEY,
        "query": actor_name
    }
    response = requests.get(search_url, params=params)
    data = response.json()

    if data["results"]:
        actor_data = data["results"][0]
        actor_id = actor_data["id"]
        profile_path = actor_data.get("profile_path")  # Get profile path from search results

        # Fetch detailed actor info
        details_url = f"{TMDB_BASE_URL}/person/{actor_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "movie_credits"
        }
        response = requests.get(details_url, params=params)
        actor_details = response.json()

        filmography = []
        for movie in actor_details.get('movie_credits', {}).get('cast', []):
            if movie.get('release_date'):
                year = movie['release_date'][:4]
                filmography.append({
                    "title": movie['title'],
                    "year": year
                })

        return {
            "name": actor_details["name"],
            "date_of_birth": actor_details.get("birthday"),
            "gender": "Male" if actor_details["gender"] == 2 else "Female",
            "date_of_death": actor_details.get("deathday"),
            "profile_path": profile_path,  # Add profile path to return data
            "filmography": filmography
        }
    return None

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

@app.post("/add_actor_from_tmdb/{actor_name}")
async def add_actor_from_tmdb(actor_name: str):
    try:
        actor_data = fetch_actor_from_tmdb(actor_name)
        if actor_data:
            added_actor = add_actor_to_neo4j(actor_data)
            return {
                "message": f"Actor {actor_name} added successfully with filmography",
                "data": {
                    "name": added_actor['name'],
                    "date_of_birth": added_actor['date_of_birth'],
                    "gender": added_actor['gender'],
                    "movies_count": len(added_actor['filmography'])
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"Actor {actor_name} not found in TMDB")
    except Exception as e:
        logging.error(f"Error adding actor from TMDB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/actors/{name}/filmography", response_model=Optional[ActorFilmography])
async def get_actor_filmography(name: str):
    cypher_query = """
    MATCH (a:Actor {name: $name})-[:ACTED_IN]->(m:Movie)
    WITH a as actor, m
    ORDER BY COALESCE(m.year, '') DESC, m.title
    WITH actor, collect(m) as movies
    RETURN actor, movies
    """
    
    result = graph.run(cypher_query, name=name).data()
    
    if not result or not result[0]['actor']:
        return None
        
    actor_data = result[0]['actor']
    movies_data = result[0]['movies']
    
    return {
        "actor": {
            "name": actor_data["name"],
            "date_of_birth": actor_data.get("date_of_birth"),
            "date_of_death": actor_data.get("date_of_death"),
            "gender": actor_data.get("gender"),
            "profile_path": actor_data.get("profile_path")
        },
        "movies": [
            {
                "title": movie["title"],
                "year": movie.get("year")
            } for movie in movies_data
        ]
    }
@app.put("/actors/{name}", response_model=Actor)
async def update_actor(name: str, actor: Optional[Actor] = None):
    try:
        actor_node = matcher.match("Actor", name=name).first()
        if not actor_node:
            raise HTTPException(status_code=404, detail="Actor not found")

        if actor:
            # Update with provided data
            actor_node.update(**actor.dict(exclude_unset=True))
            graph.push(actor_node)
        else:
            # Update from TMDB
            # Search for actor in TMDB
            search_url = f"{TMDB_BASE_URL}/search/person"
            params = {
                "api_key": TMDB_API_KEY,
                "query": name
            }
            response = requests.get(search_url, params=params)
            data = response.json()

            if not data["results"]:
                return {"message": "No updates available from TMDB"}

            actor_data = data["results"][0]
            actor_id = actor_data["id"]
            
            # Fetch detailed actor info
            details_url = f"{TMDB_BASE_URL}/person/{actor_id}"
            params = {
                "api_key": TMDB_API_KEY,
                "append_to_response": "movie_credits"
            }
            details_response = requests.get(details_url, params=params)
            actor_details = details_response.json()
            
            # Update actor in Neo4j
            cypher_query = """
            MATCH (a:Actor {name: $name})
            SET a.profile_path = $profile_path,
                a.gender = CASE WHEN $gender = 2 THEN 'Male' WHEN $gender = 1 THEN 'Female' ELSE a.gender END,
                a.date_of_birth = COALESCE($birthday, a.date_of_birth),
                a.date_of_death = COALESCE($deathday, a.date_of_death)
            RETURN a
            """
            
            result = graph.run(cypher_query, {
                'name': name,
                'profile_path': actor_data.get('profile_path'),
                'gender': actor_details.get('gender'),
                'birthday': actor_details.get('birthday'),
                'deathday': actor_details.get('deathday')
            }).data()

            if result:
                logging.info(f"Actor updated from TMDB: {name}")
                return {
                    "message": "Actor updated successfully",
                    "data": result[0]['a']
                }
                
            return {"message": "No updates available"}
            
    except Exception as e:
        logging.error(f"Error updating actor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/{title}/cast")
async def get_movie_cast(title: str):
    cypher_query = """
    MATCH (m:Movie {title: $title})
    OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
    WITH m as movie, collect(a) as unsorted_actors
    WITH movie, [actor in unsorted_actors | actor {.*}] as actors_data
    RETURN movie, apoc.coll.sort(actors_data, '^.name') as actors
    """
    
    # If you don't have APOC installed, use this simpler query instead:
    alternative_query = """
    MATCH (m:Movie {title: $title})
    OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
    WITH m as movie, a
    ORDER BY a.name
    WITH movie, collect(a) as actors
    RETURN movie, actors
    """
    
    try:
        # Try with APOC first
        result = graph.run(cypher_query, title=title).data()
    except Exception:
        # Fall back to alternative query if APOC is not available
        result = graph.run(alternative_query, title=title).data()
    
    if not result or not result[0]['movie']:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    movie_data = result[0]['movie']
    actors_data = result[0]['actors']
    
    return {
        "movie": {
            "title": movie_data["title"],
            "year": movie_data.get("year")
        },
        "actors": [
            {
                "name": actor["name"]
            } for actor in actors_data if actor  # Filter out None values
        ]
    }

@app.get("/movie/poster/{title}")
async def get_movie_poster(title: str):
    try:
        # Search for movie in TMDB
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "year": None  # You could add year if available for more accurate results
        }
        
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if data["results"]:
            # Return the first result's poster path
            return {
                "poster_path": data["results"][0]["poster_path"],
                "tmdb_id": data["results"][0]["id"]
            }
        else:
            return {"poster_path": None, "tmdb_id": None}
            
    except Exception as e:
        logging.error(f"Error fetching movie poster: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    try:
        # Test Neo4j connection
        neo4j_status = graph.run("RETURN 1").evaluate() == 1
    except Exception:
        neo4j_status = False

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "neo4j": "up" if neo4j_status else "down",
            "api": "up"
        }
    }

@app.post("/seed/actors")
async def seed_actors():
    """
    Seed a predefined list of 100 actors (50 male, 50 female) into the database.
    Includes both current and deceased actors.
    """
    actors_to_seed = {
        # Male Actors (50)
        # Deceased actors marked with † at the end
        "male": [
            "Morgan Freeman",
            "Tom Hanks",
            "Leonardo DiCaprio",
            "Denzel Washington",
            "Robert Downey Jr.",
            "Brad Pitt",
            "Christian Bale",
            "Samuel L. Jackson",
            "Johnny Depp",
            "Will Smith",
            "Matt Damon",
            "Gary Oldman",
            "Anthony Hopkins",
            "Michael Caine",
            "Harrison Ford",
            "Al Pacino",
            "Robert De Niro",
            "Tom Cruise",
            "Christopher Walken",
            "Ian McKellen",
            "Joaquin Phoenix",
            "Daniel Day-Lewis",
            "Russell Crowe",
            "Hugh Jackman",
            "Edward Norton",
            "Kevin Spacey",
            "George Clooney",
            "Bruce Willis",
            "Tommy Lee Jones",
            "Sean Connery †",    # Deceased 2020
            "Robin Williams †",   # Deceased 2014
            "Philip Seymour Hoffman †",  # Deceased 2014
            "Heath Ledger †",     # Deceased 2008
            "Paul Newman †",      # Deceased 2008
            "Marlon Brando †",    # Deceased 2004
            "Gregory Peck †",     # Deceased 2003
            "James Stewart †",    # Deceased 1997
            "Humphrey Bogart †",  # Deceased 1957
            "Clark Gable †",      # Deceased 1960
            "Charlie Chaplin †",  # Deceased 1977
            "Benedict Cumberbatch",
            "Tom Hardy",
            "Michael Fassbender",
            "Ryan Gosling",
            "Jake Gyllenhaal",
            "Idris Elba",
            "Chris Hemsworth",
            "Robert Pattinson",
            "Timothée Chalamet",
            "Chadwick Boseman †"  # Deceased 2020
        ],
        # Female Actors (50)
        # Deceased actors marked with † at the end
        "female": [
            "Meryl Streep",
            "Cate Blanchett",
            "Viola Davis",
            "Nicole Kidman",
            "Julia Roberts",
            "Emma Stone",
            "Jennifer Lawrence",
            "Scarlett Johansson",
            "Charlize Theron",
            "Helen Mirren",
            "Kate Winslet",
            "Judi Dench",
            "Sandra Bullock",
            "Angelina Jolie",
            "Jessica Chastain",
            "Amy Adams",
            "Emma Thompson",
            "Glenn Close",
            "Michelle Pfeiffer",
            "Sigourney Weaver",
            "Jodie Foster",
            "Susan Sarandon",
            "Frances McDormand",
            "Diane Keaton",
            "Julie Andrews",
            "Maggie Smith",
            "Audrey Hepburn †",   # Deceased 1993
            "Elizabeth Taylor †",  # Deceased 2011
            "Katharine Hepburn †", # Deceased 2003
            "Ingrid Bergman †",    # Deceased 1982
            "Marilyn Monroe †",    # Deceased 1962
            "Grace Kelly †",       # Deceased 1982
            "Vivien Leigh †",      # Deceased 1967
            "Bette Davis †",       # Deceased 1989
            "Lauren Bacall †",     # Deceased 2014
            "Margot Robbie",
            "Emma Watson",
            "Anne Hathaway",
            "Natalie Portman",
            "Michelle Williams",
            "Rachel McAdams",
            "Saoirse Ronan",
            "Emily Blunt",
            "Marion Cotillard",
            "Julianne Moore",
            "Brie Larson",
            "Lupita Nyong'o",
            "Zendaya",
            "Florence Pugh",
            "Olivia Colman"
        ]
    }
    
    try:
        results = {
            "success": [],
            "failed": [],
            "stats": {
                "male": {"created": 0, "skipped": 0, "failed": 0},
                "female": {"created": 0, "skipped": 0, "failed": 0}
            }
        }
        
        # Process all actors
        for gender, actors in actors_to_seed.items():
            for actor_name in actors:
                # Remove the † marker if present
                clean_name = actor_name.replace(" †", "")
                
                try:
                    # Check if actor already exists
                    existing_actor = matcher.match("Actor", name=clean_name).first()
                    
                    if existing_actor:
                        results["success"].append({
                            "name": clean_name,
                            "gender": gender,
                            "status": "skipped - already exists"
                        })
                        results["stats"][gender]["skipped"] += 1
                        continue
                    
                    # Fetch data from TMDB and create actor
                    actor_data = fetch_actor_from_tmdb(clean_name)
                    if actor_data:
                        add_actor_to_neo4j(actor_data)
                        results["success"].append({
                            "name": clean_name,
                            "gender": gender,
                            "status": "created",
                            "movies_added": len(actor_data.get('filmography', []))
                        })
                        results["stats"][gender]["created"] += 1
                    else:
                        raise Exception("No data found in TMDB")
                    
                except Exception as e:
                    results["failed"].append({
                        "name": clean_name,
                        "gender": gender,
                        "error": str(e)
                    })
                    results["stats"][gender]["failed"] += 1
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
        summary = {
            "total_attempted": len(actors_to_seed["male"]) + len(actors_to_seed["female"]),
            "total_successful": len(results["success"]),
            "total_failed": len(results["failed"]),
            "gender_stats": results["stats"],
            "details": results
        }
        
        logging.info(f"Seeded actors - Success: {summary['total_successful']}, Failed: {summary['total_failed']}")
        return summary
        
    except Exception as e:
        logging.error(f"Error seeding actors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tmdb/request-token")
async def request_token():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"https://api.themoviedb.org/3/authentication/token/new?api_key={TMDB_API_KEY}")
        data = res.json()
        return {"request_token": data["request_token"]}

@app.get("/tmdb/create-session")
async def create_session(request_token: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.themoviedb.org/3/authentication/session/new?api_key={TMDB_API_KEY}",
            json={"request_token": request_token}
        )
        data = res.json()
        return {"session_id": data["session_id"]}

@app.get("/tmdb/account")
async def get_account(session_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.themoviedb.org/3/account?api_key={TMDB_API_KEY}&session_id={session_id}"
        )
        data = res.json()
        return {
            "id": data["id"],
            "name": data.get("name") or data.get("username"),
            "avatar": data.get("avatar")
        }

@app.get("/tmdb/rated-movies")
async def get_rated_movies(session_id: str):
    # Step 1: get account ID
    async with httpx.AsyncClient() as client:
        account_res = await client.get(
            f"https://api.themoviedb.org/3/account",
            params={"api_key": TMDB_API_KEY, "session_id": session_id}
        )
        account_data = account_res.json()
        account_id = account_data["id"]

        # Step 2: get rated movies
        rated_res = await client.get(
            f"https://api.themoviedb.org/3/account/{account_id}/rated/movies",
            params={"api_key": TMDB_API_KEY, "session_id": session_id}
        )
        return rated_res.json()


# FastAPI backend
@app.get("/tmdb/favorites")
async def get_favorite_movies(session_id: str, page: int = Query(1, ge=1)):
    async with httpx.AsyncClient() as client:
        # Step 1: Get account_id
        account_res = await client.get(
            f"https://api.themoviedb.org/3/account",
            params={"api_key": TMDB_API_KEY, "session_id": session_id}
        )
        account_data = account_res.json()
        account_id = account_data["id"]

        # Step 2: Get favorite movies
        fav_res = await client.get(
            f"https://api.themoviedb.org/3/account/{account_id}/favorite/movies",
            params={"api_key": TMDB_API_KEY, "session_id": session_id, "page": page, "sort_by": "created_at.desc"}
        )
        # print(fav_res.json())
        return fav_res.json()



# Update root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return get_html_content()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

