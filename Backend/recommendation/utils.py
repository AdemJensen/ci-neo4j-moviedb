from pathlib import Path
import pandas as pd
from .predict_newuser import build_liked_list_from_preferences
from .model_based_cf import SVDRecommender

print("Loading recommendation essentials...")
links_df = pd.read_csv(Path(__file__).parent / "TheMoviesDataset/links.csv", dtype={"tmdbId": str})  # Ensure imdbId is treated as string
tmdb_df = pd.read_csv(Path(__file__).parent / "TMDB_movie_dataset_v11.csv")  # Your cleaned TMDB dataset
movielens_df = pd.read_csv(Path(__file__).parent / "TheMoviesDataset/movies.csv")  # with movieId, title, genres
movie_meta_df = pd.read_csv(Path(__file__).parent / "TheMoviesDataset/movies_metadata.csv", dtype={"id": str})
recommender = SVDRecommender()
recommender.load(Path(__file__).parent / "svd_model_500/")
print("Recommendation essentials loaded successfully.")

def movieId_to_tmdbId(movie_id):
    result = links_df[links_df['movieId'] == movie_id]['tmdbId']
    return result.iloc[0] if not result.empty else None

def tmdbId_to_movieId(imdb_id):
    result = links_df[links_df['tmdbId'] == imdb_id]['movieId']
    return result.iloc[0] if not result.empty else None

def batch_tmdbId_to_movieId(tmdb_ids):
    result = links_df[links_df['tmdbId'].isin(tmdb_ids)]['movieId']
    # return list
    return result.tolist() if not result.empty else []

def batch_movieId_to_tmdbId(movie_ids):
    result = links_df[links_df['movieId'].isin(movie_ids)]['tmdbId']
    # return list
    return result.tolist() if not result.empty else []

def get_mata(movie_id):
    # filter by movieId
    df = movie_meta_df[movie_meta_df['id'] == str(int(movie_id))]
    if df.empty:
        return None
    # convert first row to dict
    # print(df.iloc[0].to_dict())
    df = df[['id', 'title', 'poster_path', 'release_date']]
    return df.iloc[0].to_dict()

def recommend_by_tmdb_movies(tmdb_ids):
    movie_ids = batch_movieId_to_tmdbId(tmdb_ids)
    return recommend_by_movies_ids(movie_ids)

def recommend_by_movies_ids(movie_ids):
    results = recommender.recommend_new_user(
        liked_movie_ids=movie_ids,
        k=60,
        refresh=True  # enable refreshable results
    )  # df[['movieId', 'title', 'predicted_rating', 'rating_count']]
    # print("Recommended movies:\n", results)
    # for each movie, get meta, and join them to a json object
    results = results[['movieId', 'predicted_rating']]
    final_results = []
    for index, row in results.iterrows():
        movie_id = row['movieId']
        meta = get_mata(movie_id)
        # print("Movie ID:", str(int(movie_id)))
        # print("Meta:", meta)
        if meta is None:
            continue
        meta['predicted_rating'] = float(row['predicted_rating'])
        final_results.append(meta)
    return final_results[:20]

def recommend_by_genres(genres, keywords):
    liked_movies = build_liked_list_from_preferences(
        tmdb_df,
        movielens_df,
        genres=genres,
        keywords=keywords,
        sample_size=20
    )

    return recommend_by_movies_ids(liked_movies)