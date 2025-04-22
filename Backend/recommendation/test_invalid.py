from model_based_cf import SVDRecommender
import pandas as pd
import re

if __name__ == "__main__":
    # Step 2. Load saved model, use the liked movies from step 1.
    recommender = SVDRecommender()
    recommender.load("svd_model_500/")

    results = recommender.recommend_new_user(
                liked_movie_ids=[527],
                k=10,
                refresh=True  # enable refreshable results
            )
    print("🎯 Your Movie Recommendations:")
    print(results[['movieId', 'title']])
