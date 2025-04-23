from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import csr_matrix
import os


class SVDRecommender:
    def __init__(self, n_components=100):
        self.n_components = n_components
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.user_factors = None
        self.item_factors = None
        self.user_enc = LabelEncoder()
        self.movie_enc = LabelEncoder()
        self.movie_ids = None
        self.movies_df = None
        self.original_ratings = pd.read_csv(Path(__file__).parent / "TheMoviesDataset/ratings.csv")

    def train(self, ratings_df, movies_df):
        self.movies_df = movies_df
        self.original_ratings = ratings_df.copy()  # ✅ Added for filtering

        ratings_df = ratings_df.dropna(subset=["userId", "movieId", "rating"]).drop_duplicates()
        ratings_df["userId"] = ratings_df["userId"].astype(int)
        ratings_df["movieId"] = ratings_df["movieId"].astype(int)

        ratings_df['user_enc'] = self.user_enc.fit_transform(ratings_df['userId'])
        ratings_df['movie_enc'] = self.movie_enc.fit_transform(ratings_df['movieId'])

        num_users = ratings_df['user_enc'].nunique()
        num_movies = ratings_df['movie_enc'].nunique()

        sparse_matrix = csr_matrix(
            (ratings_df['rating'], (ratings_df['user_enc'], ratings_df['movie_enc'])),
            shape=(num_users, num_movies)
        )

        self.user_factors = self.svd.fit_transform(sparse_matrix)
        self.item_factors = self.svd.components_.T
        self.movie_ids = self.movie_enc.classes_

    def recommend_existing_user(self, user_id, k=10, min_ratings=100, filter_seen=True):
        if user_id not in self.user_enc.classes_:
            raise ValueError("User not found in training data.")

        u_idx = self.user_enc.transform([user_id])[0]
        user_vec = self.user_factors[u_idx]
        scores = np.dot(user_vec, self.item_factors.T)
        scores = np.clip(scores, 1.0, 5.0)

        if filter_seen:
            # Remove movies already rated by the user
            seen_movies = self.original_ratings[self.original_ratings['userId'] == user_id]['movieId'].values
            seen_encs = [self.movie_enc.transform([m])[0] for m in seen_movies if m in self.movie_enc.classes_]
            scores[seen_encs] = -np.inf  # Exclude seen movies

        # Get top-K movie indices
        top_idx = np.argsort(scores)[::-1]
        top_movie_ids = self.movie_ids[top_idx]
        top_scores = scores[top_idx]

        # Assemble recommendations
        recs_df = pd.DataFrame({
            'movieId': top_movie_ids,
            'predicted_rating': top_scores
        }).merge(self.movies_df, on='movieId', how='left')

        # Add rating count
        rating_counts = self.original_ratings['movieId'].value_counts()
        recs_df['rating_count'] = recs_df['movieId'].map(rating_counts)

        # Filter by popularity only
        filtered = recs_df[recs_df['rating_count'] >= min_ratings]
        filtered = filtered.sort_values('predicted_rating', ascending=False)

        return filtered.head(k)[['movieId', 'title', 'predicted_rating', 'rating_count']]

    def recommend_new_user(self, liked_movie_ids=None, k=10, min_ratings=100, refresh=False, sample_from_top_n=100):
        if not liked_movie_ids:
            rating_counts = self.original_ratings['movieId'].value_counts()
            popular_movies = rating_counts[rating_counts >= min_ratings].index
            df = self.movies_df[self.movies_df['movieId'].isin(popular_movies)].copy()
            df['predicted_rating'] = 4.0  # Placeholder rating
            df['rating_count'] = df['movieId'].map(rating_counts)

            if refresh:
                df = df.sample(n=min(k, len(df)), random_state=None)
            else:
                df = df.sort_values('rating_count', ascending=False).head(k)

            return df[['movieId', 'title', 'predicted_rating', 'rating_count']]

        # Get encoded movie indices
        liked_encs = [self.movie_enc.transform([mid])[0]
                      for mid in liked_movie_ids if mid in self.movie_enc.classes_]

        if not liked_movie_ids or len(liked_encs) == 0:
            # fallback
            rating_counts = self.original_ratings['movieId'].value_counts()
            popular_movies = rating_counts[rating_counts >= min_ratings].head(k).index
            df = self.movies_df[self.movies_df['movieId'].isin(popular_movies)].copy()
            df['predicted_rating'] = 4.0  # Default score
            df['rating_count'] = df['movieId'].map(rating_counts)

            if refresh:
                df = df.sample(n=min(k, len(df)), random_state=None)
            else:
                df = df.sort_values('rating_count', ascending=False).head(k)

            return df[['movieId', 'title', 'predicted_rating', 'rating_count']]

        # Compute scores
        user_vec = self.item_factors[liked_encs].mean(axis=0)
        scores = np.dot(self.item_factors, user_vec)
        scores[liked_encs] = -np.inf  # Don’t recommend liked ones
        scores = np.clip(scores, 1.0, 5.0)

        # Rank all
        top_idx = np.argsort(scores)[::-1]
        top_movie_ids = self.movie_ids[top_idx]
        top_scores = scores[top_idx]

        recs_df = pd.DataFrame({'movieId': top_movie_ids, 'predicted_rating': top_scores})
        recs_df = recs_df.merge(self.movies_df, on='movieId', how='left')

        # Add popularity filter
        rating_counts = self.original_ratings['movieId'].value_counts()
        recs_df['rating_count'] = recs_df['movieId'].map(rating_counts)
        recs_df = recs_df[recs_df['rating_count'] >= min_ratings]

        # Refresh logic
        if refresh:
            pool = recs_df.head(sample_from_top_n)
            recs_df = pool.sample(n=min(k, len(pool)), random_state=None)
        else:
            recs_df = recs_df.head(k)

        return recs_df[['movieId', 'title', 'predicted_rating', 'rating_count']]

    def save(self, path):
        os.makedirs(path, exist_ok=True)
        np.save(os.path.join(path, "user_factors.npy"), self.user_factors)
        np.save(os.path.join(path, "item_factors.npy"), self.item_factors)
        np.save(os.path.join(path, "movie_ids.npy"), self.movie_ids)
        np.save(os.path.join(path, "user_enc_classes.npy"), self.user_enc.classes_)
        np.save(os.path.join(path, "movie_enc_classes.npy"), self.movie_enc.classes_)
        self.movies_df.to_csv(os.path.join(path, "movies.csv"), index=False)

    def load(self, path):
        self.user_factors = np.load(os.path.join(path, "user_factors.npy"))
        self.item_factors = np.load(os.path.join(path, "item_factors.npy"))
        self.movie_ids = np.load(os.path.join(path, "movie_ids.npy"))
        self.user_enc.classes_ = np.load(os.path.join(path, "user_enc_classes.npy"), allow_pickle=True)
        self.movie_enc.classes_ = np.load(os.path.join(path, "movie_enc_classes.npy"), allow_pickle=True)
        self.movies_df = pd.read_csv(os.path.join(path, "movies.csv"))


if __name__ == "__main__":
    # Load data
    ratings_df = pd.read_csv("TheMoviesDataset/ratings.csv")
    movies_df = pd.read_csv("TheMoviesDataset/movies.csv")

    # Train
    recommender = SVDRecommender(n_components=500)
    recommender.train(ratings_df, movies_df)

    # Save model
    recommender.save("svd_model_500/")
