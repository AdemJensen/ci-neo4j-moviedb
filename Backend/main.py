from mcp import *
from recommendation import recommend_by_tmdb_movies
from neo4j import add_movie_to_neo4j
from tmdb import fetch_movie_from_tmdb
from tmdb import fetch_actor_from_tmdb
from tmdb import get_favorite_movies as get_favorite_movies_tmdb
from neo4j import add_actor_to_neo4j
from config import *
from models import *
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from py2neo import Node, Relationship
from typing import Optional, List
import logging
import requests
import httpx
from datetime import datetime
from pathlib import Path
import socketio
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode='asgi')
main_app = socketio.ASGIApp(sio, other_asgi_app=app)


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


@app.post("/add_movie_from_tmdb/{movie_title}")
async def add_actor_from_tmdb(movie_title: str):
    try:
        movie_data = fetch_movie_from_tmdb(movie_title)
        if movie_data:
            added_movie = add_movie_to_neo4j(movie_data)
            return {
                "message": f"Movie {movie_title} added successfully with casts",
                "data": {
                    "title": added_movie['title'],
                    "year": added_movie['year']
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"Movie {movie_title} not found in TMDB")
    except Exception as e:
        logging.error(f"Error adding actor from TMDB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
    from seed_actors import seed_actors as seed_actors_func
    return await seed_actors_func()


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


@app.get("/tmdb/favorites")
async def get_favorite_movies(session_id: str, page: int = Query(1, ge=1)):
    return await get_favorite_movies_tmdb(session_id, page)


@app.get("/recommendations")
async def get_recommend_movies(session_id: str):
    favorite_movies = await get_favorite_movies_tmdb(session_id, 1)
    # for each movie, get id
    tmdb_ids = [movie["id"] for movie in favorite_movies["results"]]
    res = recommend_by_tmdb_movies(tmdb_ids)
    # print("Recommended movies:", res)
    return {
        "results": res,
    }


class RecommendInput(BaseModel):
    genre: str
    country: str
    language: str
    year_range: str
    description: str


@app.post("/form-recommendations")
async def recommend_movie_by_form(data: RecommendInput):
    print("Received form data:", data)
    prompt = (
        f"Please recommend a movie based on the following preferences:\n"
        f"Genre: {data.genre}; Country: {data.country}; Language: {data.language}; Release Period: {data.year_range}.\n"
        f"User Description: {data.description}\n\n"
        f"Provide the movie title, a short summary, and the reason for your recommendation."
    )

    headers = {
        "Authorization": f"Bearer " + SILICONFLOW_SK,
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers,
                             json={
                                 "model": SILICONFLOW_MODEL,
                                 "messages": [{"role": "user", "content": prompt}],
                                 "stream": False,
                                 "temperature": 0.5
                             })
        result = resp.json()
        answer = result["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Error generating recommendation: {str(e)}")
        answer = "❌ Failed to generate recommendation. Please try again later."

    return {"recommendation": answer}


# Update root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return get_html_content()


# Socket.IO 接口
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


@sio.event
async def session_request(sid, data):
    await sio.emit("session_confirm", {"session_id": sid}, to=sid)


@sio.event
async def user_uttered(sid, data):
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, user_uttered_handle, sio, loop, sid, data)
    print(f"User uttered: {data}, handle is over.")


if __name__ == "__main__":
    import uvicorn

    if SILICONFLOW_SK == "":
        logger.warning("SILICONFLOW_SK is not set. Bot chatting is disabled.")
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    else:
        uvicorn.run(main_app, host="0.0.0.0", port=PORT)
