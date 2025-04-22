import requests
import csv
import logging
import time
import json
import os
from py2neo import Graph, Node, Relationship


def get_actor_details(actor_name):
    search_url = f"{TMDB_BASE_URL}/search/person"
    params = {
        "api_key": TMDB_API_KEY,
        "query": actor_name
    }
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
        data = response.json()
        
        if 'results' not in data:
            logging.error(f"Unexpected API response for {actor_name}: {json.dumps(data)}")
            return None
        if not data['results']:
            logging.warning(f"No results found for actor: {actor_name}")
            return None
        
        actor_id = data['results'][0]['id']
        
        details_url = f"{TMDB_BASE_URL}/person/{actor_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "movie_credits"
        }
        response = requests.get(details_url, params=params)
        response.raise_for_status()
        actor_data = response.json()
        
        return actor_data
    except requests.RequestException as e:
        logging.error(f"API request failed for {actor_name}: {str(e)}")
        return None

def extract_actor_info(actor_data):
    name = actor_data['name']
    dob = actor_data.get('birthday', 'Unknown')
    gender = "Male" if actor_data['gender'] == 2 else "Female" if actor_data['gender'] == 1 else "Unknown"
    dod = actor_data.get('deathday', 'N/A')
    
    movies = []
    for movie in actor_data.get('movie_credits', {}).get('cast', []):
        if 'release_date' in movie and movie['release_date']:
            year = movie['release_date'][:4]
            movies.append((movie['title'], year))
    
    return name, dob, gender, dod, movies

def export_to_csv(all_actor_data, filename):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Name', 'Date of Birth', 'Gender', 'Date of Death', 'Movie Title', 'Year'])
            
            for actor_data in all_actor_data:
                if actor_data:
                    name, dob, gender, dod, movies = actor_data
                    for movie in movies:
                        csvwriter.writerow([name, dob, gender, dod, movie[0], movie[1]])
        
        logging.info(f"Data successfully exported to {filename}")
        print(f"Data exported to {filename}")
    except Exception as e:
        logging.error(f"Error exporting to CSV: {str(e)}")
        print(f"Error exporting to CSV: {str(e)}")

def export_to_neo4j(data_file):
    try:
        # 1. (Optional) Clear existing data
        graph.run("MATCH (n) DETACH DELETE n")

        # 2. Open the file and read line by line using csv.reader
        with open(data_file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # If your file has a header row, uncomment the next line to skip it:
            # next(reader, None)  # Skip header
            
            for row in reader:
                # We expect 6 columns: name, dob, gender, dod, movie_title, movie_year
                if len(row) < 6:
                    logging.warning(f"Skipping malformed row: {row}")
                    continue
                
                name, dob, gender, dod, movie_title, movie_year = row

                # 3. Create/Merge Actor node
                actor_node = Node(
                    "Actor",
                    name=name.strip() if name else None,
                    date_of_birth=dob.strip() if dob else None,
                    gender=gender.strip() if gender else None,
                    date_of_death=dod.strip() if dod else None
                )
                # Merge ensures we don't create duplicates if "name" already exists
                graph.merge(actor_node, "Actor", "name")

                # 4. Create/Merge Movie node
                movie_node = Node(
                    "Movie",
                    title=movie_title.strip() if movie_title else None,
                    year=movie_year.strip() if movie_year else None
                )
                graph.merge(movie_node, "Movie", "title")

                # 5. Create relationship :ACTED_IN
                acted_in_rel = Relationship(actor_node, "ACTED_IN", movie_node)
                graph.merge(acted_in_rel, "Actor", "name")  # or simply use graph.create(acted_in_rel)
        
        logging.info("Data successfully exported to Neo4j")
        print("Data successfully exported to Neo4j")

    except Exception as e:
        logging.error(f"Error exporting to Neo4j: {str(e)}")
        print(f"Error exporting to Neo4j: {str(e)}")

def process_actors_from_file(input_file):
    all_actor_data = []
    actors_with_no_data = []
    
    try:
        with open(input_file, 'r') as file:
            actor_names = file.read().splitlines()
        
        for actor_name in actor_names:
            print(f"Processing {actor_name}...")
            actor_data = get_actor_details(actor_name.strip())
            if actor_data:
                processed_data = extract_actor_info(actor_data)
                all_actor_data.append(processed_data)
            else:
                actors_with_no_data.append(actor_name)
            time.sleep(0.25)  # TMDb API allows 40 requests per 10 seconds
        
        if actors_with_no_data:
            logging.warning(f"No data found for the following actors: {', '.join(actors_with_no_data)}")
            print(f"No data found for: {', '.join(actors_with_no_data)}")
        
        return all_actor_data
    except FileNotFoundError:
        logging.error(f"Input file {input_file} not found")
        print(f"Input file {input_file} not found. Please create this file with a list of actor names, one per line.")
        return []
    except Exception as e:
        logging.error(f"Error processing actors from file: {str(e)}")
        print(f"Error processing actors from file: {str(e)}")
        return []
    

def extract_actor_names(input_file, output_file):
    actors = set()

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(input_file, encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cast_json = row.get("cast", "")
                if cast_json:
                    try:
                        cast_list = json.loads(cast_json)
                        for actor in cast_list:
                            name = actor.get("name")
                            if name:
                                actors.add(name)
                    except Exception as e:
                        print(f"Error parsing cast for movie_id {row.get('movie_id')}: {e}")
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        return

    # Write the unique actor names to the output file
    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            for name in sorted(actors):
                outfile.write(name.strip() + "\n")
        print(f"Extracted {len(actors)} unique actor names to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")

# Main execution
# Set up logging
logging.basicConfig(filename='tmdb_scraper_log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# TMDb API setup
TMDB_API_KEY = "26c6cb2a845b3607026e16b046f0ee1d"  # Replace with your actual TMDb API key
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Neo4j connection setup
NEO4J_URI = "bolt://localhost:7687"  # Update this with your Neo4j URI
NEO4J_USER = "neo4j"  # Update this with your Neo4j username
NEO4J_PASSWORD = "12345678"  # Update this with your Neo4j password

graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

logging.info("Script started")
actor_file = 'actors.txt'
output_file = 'actors_movies_tmdb.csv'
extract_actor_names("tmdb_5000_credits.csv", actor_file)
all_actor_data = process_actors_from_file(actor_file)
if all_actor_data:
    export_to_csv(all_actor_data, output_file)
else:
    logging.warning("No valid actor data to export")
    print("No valid actor data to export")
logging.info("Script finished")

export_to_neo4j(output_file)