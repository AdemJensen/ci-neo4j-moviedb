# setup the environment
from .prepare_env import setup_model_data_auto

setup_model_data_auto()




# export necessary functions
from .utils import recommend_by_tmdb_movies, recommend_by_genres
