from .model_based_cf import SVDRecommender
import pandas as pd
import re


def extract_tmdb_filter_options(df, save_dir=None):
    """
    Get all filtering options
    """
    import os

    def parse_comma_separated(x):
        if pd.isna(x):
            return []
        return [s.strip() for s in str(x).split(",") if s.strip()]

    # Genres
    df["genres"] = df["genres"].apply(parse_comma_separated)
    all_genres = sorted(set(g for sublist in df["genres"] for g in sublist))

    # Keywords
    df["keywords"] = df["keywords"].apply(parse_comma_separated)
    all_keywords = sorted(set(k for sublist in df["keywords"] for k in sublist))

    # Languages
    all_languages = sorted(df["original_language"].dropna().unique())

    # Year range
    df["year"] = pd.to_datetime(df["release_date"], errors='coerce').dt.year
    min_year = int(df["year"].min())
    max_year = int(df["year"].max())

    # Optional saving
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

        pd.DataFrame({"genre": all_genres}).to_csv(os.path.join(save_dir, "genres.csv"), index=False)
        pd.DataFrame({"keyword": all_keywords}).to_csv(os.path.join(save_dir, "keywords.csv"), index=False)
        pd.DataFrame({"language": all_languages}).to_csv(os.path.join(save_dir, "languages.csv"), index=False)
        pd.DataFrame([{"min_year": min_year, "max_year": max_year}]).to_csv(os.path.join(save_dir, "year_range.csv"), index=False)

    return {
        "genres": all_genres,
        "keywords": all_keywords,
        "languages": all_languages,
        "year_range": (min_year, max_year)
    }



def build_liked_list_from_preferences(tmdb_df,
                                      movielens_df,
                                      genres=None,
                                      keywords=None,
                                      sample_size=10):
    """
    Simulate a cold-start liked list from user-selected filters.
    Returns a list of MovieLens movieIds using title matching.
    Only filters on genres and keywords.
    """
    genres = genres or []
    keywords = keywords or []

    # Normalize filter values for case-insensitive matching
    genres = set(g.lower() for g in genres)
    keywords = set(k.lower() for k in keywords)

    # Ensure text columns are strings
    tmdb_df['genres'] = tmdb_df['genres'].astype(str)
    tmdb_df['keywords'] = tmdb_df['keywords'].astype(str)

    def is_representative(row):
        genre_text = row['genres'].lower()
        keyword_text = row['keywords'].lower()

        genre_match = any(g in genre_text for g in genres) if genres else True
        keyword_match = any(k in keyword_text for k in keywords) if keywords else True

        return genre_match and keyword_match

    # Filter TMDB movies
    filtered = tmdb_df[tmdb_df.apply(is_representative, axis=1)]
    print(f"🎯 Filtered down to {len(filtered)} candidate movies from TMDB.")

    if filtered.empty:
        print("⚠️ No matching movies found.")
        return []

    # Sample some candidates
    sampled = filtered.sample(n=min(sample_size, len(filtered)), random_state=42)

    # Clean MovieLens titles for better matching (move "The" from end to front)
    def normalize_movielens_title(title):
        match = re.match(r"^(.*),\s*The\s*(\(\d{4}\))?$", title)
        if match:
            main = match.group(1).strip()
            year = match.group(2) if match.group(2) else ""
            return f"The {main}".strip().lower()
        return re.sub(r"\(\d{4}\)", "", title).strip().lower()

    movielens_df['clean_title'] = movielens_df['title'].apply(normalize_movielens_title)

    # Match titles
    liked_ids = []

    print("\n👍 Simulated liked movies (matched to MovieLens):")
    for _, row in sampled.iterrows():
        tmdb_title = str(row['title']).strip().lower()
        matched = movielens_df[movielens_df['clean_title'] == tmdb_title]

        if not matched.empty:
            movie_id = matched.iloc[0]['movieId']
            liked_ids.append(movie_id)
            print(f"🎬 {row['title']} → ML ID: {movie_id}")
        else:
            print(f"❌ {row['title']} not found in MovieLens")

    return liked_ids





if __name__ == "__main__":
    tmdb_df = pd.read_csv("TMDB_movie_dataset_v11.csv")  # Your cleaned TMDB dataset
    movielens_df = pd.read_csv("TheMoviesDataset/movies.csv")  # with movieId, title, genres

    # Step 1. new users choose the movie they like by options from tmdb dataset.
    # the result movies are found in the ml dataset.
    liked_movies = build_liked_list_from_preferences(
        tmdb_df,
        movielens_df,
        genres=["Comedy", "Romance"],
        keywords=["high school", "friendship"],
        sample_size=20
    )

    # May also use this for the first round of recommendation (direct filtering)
    print("Sampled liked movies for cold-start:", liked_movies)


    # Step 2. Load saved model, use the liked movies from step 1.
    recommender = SVDRecommender()
    recommender.load("svd_model_500/")

    results = recommender.recommend_new_user(
                liked_movie_ids=liked_movies,
                k=10,
                refresh=True  # enable refreshable results
            )
    print("🎯 Your Movie Recommendations:")
    print(results[['movieId', 'title']])

    # print("🎬 Welcome to the Movie Recommender System!")
    # print("You are acting as a NEW user.")

    # # User input
    # liked_input = input("👉 Enter a few liked movie IDs separated by commas (or leave blank if no history): ").strip()
    #
    #
    # if liked_input:
    #     try:
    #         liked_movies = [int(x.strip()) for x in liked_input.split(",") if x.strip().isdigit()]
    #     except Exception as e:
    #         print(f"⚠️ Invalid input: {e}")
    #         liked_movies = []
    # else:
    #     liked_movies = None
    #
    # print("\n✅ Generating recommendations... (type 'r' to refresh, 'q' to quit)\n")
    #
    # while True:
    #     try:
    #         # input list of liked movie ids in movielens, [] indicates a cold start
    #         results = recommender.recommend_new_user(
    #             liked_movie_ids=liked_movies1,
    #             k=10,
    #             refresh=True  # enable refreshable results
    #         )
    #         print("🎯 Your Movie Recommendations:")
    #         print(results[['movieId', 'title']])
    #     except Exception as e:
    #         print("⚠️ Error generating recommendations:", e)
    #
    #     # Next action
    #     next_action = input("\n🔁 Press [r] to refresh, [q] to quit: ").strip().lower()
    #     if next_action == 'q':
    #         break
    #     elif next_action != 'r':
    #         print("❓ Invalid input. Type 'r' to refresh or 'q' to quit.\n")
