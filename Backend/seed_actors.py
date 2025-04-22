from fastapi import HTTPException
import asyncio

from Backend.neo4j import add_actor_to_neo4j
from Backend.tmdb import fetch_actor_from_tmdb
from config import *


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
            "Sean Connery †",  # Deceased 2020
            "Robin Williams †",  # Deceased 2014
            "Philip Seymour Hoffman †",  # Deceased 2014
            "Heath Ledger †",  # Deceased 2008
            "Paul Newman †",  # Deceased 2008
            "Marlon Brando †",  # Deceased 2004
            "Gregory Peck †",  # Deceased 2003
            "James Stewart †",  # Deceased 1997
            "Humphrey Bogart †",  # Deceased 1957
            "Clark Gable †",  # Deceased 1960
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
            "Audrey Hepburn †",  # Deceased 1993
            "Elizabeth Taylor †",  # Deceased 2011
            "Katharine Hepburn †",  # Deceased 2003
            "Ingrid Bergman †",  # Deceased 1982
            "Marilyn Monroe †",  # Deceased 1962
            "Grace Kelly †",  # Deceased 1982
            "Vivien Leigh †",  # Deceased 1967
            "Bette Davis †",  # Deceased 1989
            "Lauren Bacall †",  # Deceased 2014
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