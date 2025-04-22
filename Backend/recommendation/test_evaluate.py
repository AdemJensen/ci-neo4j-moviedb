import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from model_based_cf import SVDRecommender
from sklearn.model_selection import train_test_split
from tqdm import tqdm


def evaluate_with_holdout(test_df, recommender, k=10, threshold=4.0, sample_users=100):
    precisions, recalls, f1s = [], [], []
    rmse_preds, rmse_actuals = [], []

    print(f"\nEvaluating with holdout on {sample_users} users...")

    users = test_df['userId'].unique()
    np.random.seed(42)
    np.random.shuffle(users)
    users = users[:sample_users]

    for user_id in tqdm(users, desc="Evaluating", unit="user"):
        user_ratings = test_df[test_df['userId'] == user_id]
        high_rated = user_ratings[user_ratings['rating'] >= threshold]

        if len(high_rated) < 2 or user_id not in recommender.user_enc.classes_:
            continue

        # Split into observed (simulate known) and hidden (simulate test)
        hidden = high_rated.sample(frac=0.5, random_state=42)
        observed = user_ratings.drop(hidden.index)

        # Get recommendations from observed, don't block the seen movies
        try:
            recs = recommender.recommend_existing_user(user_id, k=k, filter_seen=False)
        except:
            continue

        recommended_ids = set(recs['movieId'].values)
        relevant_ids = set(hidden['movieId'].values)
        num_hits = len(recommended_ids & relevant_ids)

        precision = num_hits / k
        recall = num_hits / len(relevant_ids)
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    # RMSE
    print("\nComputing RMSE...")
    valid_df = test_df[test_df['userId'].isin(recommender.user_enc.classes_)]
    valid_df = valid_df[valid_df['movieId'].isin(recommender.movie_enc.classes_)]
    valid_df['user_enc'] = recommender.user_enc.transform(valid_df['userId'])
    valid_df['movie_enc'] = recommender.movie_enc.transform(valid_df['movieId'])

    rmse_sample = valid_df.sample(n=min(100_000, len(valid_df)), random_state=42)

    for _, row in tqdm(rmse_sample.iterrows(), total=len(rmse_sample), desc="RMSE"):
        u, m = int(row['user_enc']), int(row['movie_enc'])
        if u < recommender.user_factors.shape[0] and m < recommender.item_factors.shape[0]:
            pred = np.dot(recommender.user_factors[u], recommender.item_factors[m])
            pred = np.clip(pred, 1.0, 5.0)
            rmse_preds.append(pred)
            rmse_actuals.append(row['rating'])

    rmse = np.sqrt(mean_squared_error(rmse_actuals, rmse_preds))

    return rmse, np.mean(precisions), np.mean(recalls), np.mean(f1s)


if __name__ == "__main__":
    # Load model
    recommender = SVDRecommender()
    recommender.load("svd_model_500/")

    # Load full dataset and split for testing
    ratings_df = pd.read_csv("TheMoviesDataset/ratings.csv")
    _, test_df = train_test_split(ratings_df, test_size=0.2, random_state=42)

    # Evaluate with holdout approach
    rmse, precision, recall, f1 = evaluate_with_holdout(test_df, recommender, k=10, threshold=4.0, sample_users=100)

    print(f"\n✅ Test RMSE:     {rmse:.4f}")
    print(f"✅ Precision@10:  {precision:.4f}")
    print(f"✅ Recall@10:     {recall:.4f}")
    print(f"✅ F1@10:         {f1:.4f}")

