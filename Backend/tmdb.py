from config import *
import requests


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


def fetch_movie_from_tmdb(title):
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }
    search_response = requests.get(search_url, params=params).json()

    if search_response["results"]:
        movie_data = search_response["results"][0]
        movie_id = movie_data["id"]

        # Get movie details + credits (cast)
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits"
        }
        details_response = requests.get(details_url, params=params).json()

        cast = []
        for actor in details_response.get("credits", {}).get("cast", []):
            if actor.get("name"):
                details_url = f"{TMDB_BASE_URL}/person/{actor.get('id')}"
                params = {
                    "api_key": TMDB_API_KEY,
                    "append_to_response": "movie_credits"
                }
                response = requests.get(details_url, params=params)
                actor_details = response.json()
                cast.append({
                    "name": actor_details["name"],
                    "date_of_birth": actor_details.get("birthday"),
                    "gender": "Male" if actor_details["gender"] == 2 else "Female",
                    "date_of_death": actor_details.get("deathday"),
                    "profile_path": actor.get("profile_path"),  # Add profile path to return data
                })

        return {
            "title": details_response["title"],
            "year": details_response.get("release_date", "")[:4],
            # "overview": details_response.get("overview"),
            "tmdb_id": movie_id,
            "cast": cast
        }

    return None