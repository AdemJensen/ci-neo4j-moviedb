from pydantic import BaseModel
from typing import List, Optional


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