"""
recommend.py
------------
TF-IDF cosine-similarity recommendation engine.

Algorithm:
  1. Each movie row is flattened to a single string of all its fields.
  2. The user's survey selections are concatenated into one preference string.
  3. TF-IDF vectorises all strings together.
  4. Cosine similarity is computed between the user vector and every movie vector.
  5. A small sentiment boost (0.1 × sentiment_score) is added.
  6. Movies the user already selected in the survey are excluded.
  7. Top N movies by final score are returned.

Fallback (empty survey): returns top N movies by vote_average.
"""

import os
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENRICHED = os.path.join(_ROOT, "Data", "movies_enriched.csv")
_RAW      = os.path.join(_ROOT, "Data", "movies_1000.csv")


def _load_data() -> pd.DataFrame:
    """Load enriched CSV if available, otherwise fall back to raw CSV."""
    if os.path.exists(_ENRICHED):
        df = pd.read_csv(_ENRICHED)
    elif os.path.exists(_RAW):
        df = pd.read_csv(_RAW)
        df["sentiment_score"] = 0.0
    else:
        raise FileNotFoundError(
            "No movie data found. Run fetch_movies.py (and optionally enrich.py) first."
        )
    # Ensure sentiment column exists and both numeric columns are proper floats
    # (CSV read can leave them as object/string dtype)
    if "sentiment_score" not in df.columns:
        df["sentiment_score"] = 0.0
    df["sentiment_score"] = pd.to_numeric(df["sentiment_score"], errors="coerce").fillna(0.0)
    df["vote_average"]    = pd.to_numeric(df["vote_average"],    errors="coerce").fillna(0.0)
    return df


def _movie_string(row: pd.Series) -> str:
    """Concatenate all metadata fields of a movie into one string."""
    fields = [
        "movie_title", "release_year", "genres",
        "director_name", "actor_1_name", "actor_2_name", "actor_3_name",
    ]
    parts = [str(row.get(f, "")) for f in fields]
    return " ".join(p for p in parts if p and p.lower() != "nan")


def recommend(
    actors:    list[str],
    directors: list[str],
    genres:    list[str],
    titles:    list[str],
    n:         int = 5,
) -> list[dict]:
    """
    Return n movie recommendation dicts.
    If all input lists are empty, returns the top-n by vote_average.
    """
    df = _load_data()

    # ── Fallback: no user input → top-rated ────────────────────────────────
    if not any([actors, directors, genres, titles]):
        top = df.nlargest(n, "vote_average")
        top = top.copy()
        top["similarity_score"] = 0.0
        top["final_score"]      = top["vote_average"]
        return _to_records(top)

    # ── Build strings ────────────────────────────────────────────────────────
    user_string   = " ".join(actors + directors + genres + titles)
    movie_strings = df.apply(_movie_string, axis=1).tolist()

    # ── TF-IDF vectorisation ─────────────────────────────────────────────────
    vectorizer  = TfidfVectorizer(stop_words="english")
    tfidf       = vectorizer.fit_transform([user_string] + movie_strings)
    user_vec    = tfidf[0]
    movie_mat   = tfidf[1:]

    sim_scores  = cosine_similarity(user_vec, movie_mat).flatten()

    # ── Score = similarity + sentiment boost ─────────────────────────────────
    sentiment   = df["sentiment_score"].fillna(0.0).values
    final       = sim_scores + 0.1 * sentiment

    df = df.copy()
    df["similarity_score"] = sim_scores
    df["final_score"]      = final

    # ── Exclude movies the user already knows ─────────────────────────────────
    # Normalise: lowercase + strip punctuation so "Schindlers List" matches
    # "Schindler's List" and similar apostrophe/hyphen variants.
    def _norm(s: str) -> str:
        return re.sub(r"[^\w\s]", "", s.lower()).strip()

    exclude = {_norm(t) for t in titles}
    df = df[~df["movie_title"].apply(lambda t: _norm(str(t))).isin(exclude)]

    top = df.nlargest(n, "final_score")
    return _to_records(top)


def _to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame rows to plain dicts, replacing NaN with empty string."""
    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            try:
                if pd.isna(v):
                    r[k] = ""
            except (TypeError, ValueError):
                pass  # non-scalar value, leave as-is
    return records
