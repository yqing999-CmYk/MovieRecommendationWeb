#!/usr/bin/env python3
"""
fetch_movies.py
---------------
Fetches up to 1000 movies from the TMDB API and saves them to
Data/movies_1000.csv.

Columns saved:
    movie_title, release_year, genres, director_name,
    actor_1_name, actor_2_name, actor_3_name,
    imdb_id, vote_average, poster_path, runtime

Usage:
    1. Set your TMDB API key:
         - Create .env in the project root with:  TMDB_API_KEY=your_key_here
         - OR export TMDB_API_KEY=your_key_here  (terminal)
    2. Run from the project root:
         python fetch_movies.py

The script supports resuming: if movies_1000.csv already exists it will
skip titles already written and continue from where it left off.

API optimisation: uses ?append_to_response=credits,external_ids so each
movie requires only ONE detail call (not three separate calls).
"""

import csv
import os
import sys
import time

import requests
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

# Look for .env in the same directory as this script (project root)
_script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_script_dir, ".env"))

API_KEY    = os.getenv("TMDB_API_KEY", "")
BASE_URL   = "https://api.themoviedb.org/3"
OUTPUT     = os.path.join(_script_dir, "Data", "movies_1000.csv")
TARGET     = 1000          # total movies to collect
DISCOVER_PAGES = 50        # 20 results/page × 50 pages = 1 000
SLEEP_SEC  = 0.26          # ≈ 3.8 req/s — well under TMDB's 40 req/10 s limit

CSV_FIELDS = [
    "movie_title", "release_year", "genres",
    "director_name", "actor_1_name", "actor_2_name", "actor_3_name",
    "imdb_id", "vote_average", "poster_path", "runtime",
]

# ── TMDB helpers ──────────────────────────────────────────────────────────────

def _get(url: str, params: dict, retries: int = 3) -> dict:
    """GET with simple retry logic."""
    params["api_key"] = API_KEY
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"    [retry {attempt+1}] {exc} — waiting {wait}s")
                time.sleep(wait)
            else:
                raise


def discover_page(page: int) -> list[dict]:
    """Return one page (up to 20) of popular movies from /discover/movie."""
    data = _get(
        f"{BASE_URL}/discover/movie",
        {
            "sort_by":         "popularity.desc",
            "vote_count.gte":  100,    # filter out movies with almost no votes
            "page":            page,
        },
    )
    return data.get("results", [])


def get_full_movie(movie_id: int) -> dict:
    """
    Single API call that returns movie details, credits, and external IDs
    combined via append_to_response.
    """
    return _get(
        f"{BASE_URL}/movie/{movie_id}",
        {"append_to_response": "credits,external_ids"},
    )


# ── Row extraction ────────────────────────────────────────────────────────────

def build_row(data: dict) -> list:
    """Extract a CSV row from a full movie detail response."""
    title        = data.get("title", "").strip()
    release_date = data.get("release_date", "")
    release_year = release_date[:4] if release_date else ""

    # genres — full detail response returns list of {"id":…, "name":…}
    genres = ", ".join(g["name"] for g in data.get("genres", []))

    vote_average = data.get("vote_average", "")
    poster_path  = data.get("poster_path", "")   # e.g. "/abc123.jpg"
    runtime      = data.get("runtime", "")

    # Credits
    crew    = data.get("credits", {}).get("crew", [])
    cast    = data.get("credits", {}).get("cast", [])
    director = next((c["name"] for c in crew if c.get("job") == "Director"), "")
    actors  = [c["name"] for c in cast[:3]]

    # IMDB ID (e.g. "tt0133093")
    imdb_id = data.get("external_ids", {}).get("imdb_id", "")

    return [
        title, release_year, genres,
        director,
        actors[0] if len(actors) > 0 else "",
        actors[1] if len(actors) > 1 else "",
        actors[2] if len(actors) > 2 else "",
        imdb_id, vote_average, poster_path, runtime,
    ]


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not API_KEY:
        print(
            "ERROR: TMDB API key not found.\n"
            "  Create Data/.env with:  TMDB_API_KEY=your_key_here\n"
            "  Or set the environment variable TMDB_API_KEY."
        )
        sys.exit(1)

    # ── Resume support: collect already-written titles ──────────────────────
    existing_titles: set[str] = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_titles.add(row.get("movie_title", "").strip())
        print(f"Resuming — {len(existing_titles)} movies already saved.")
    else:
        print(f"Starting fresh — will write to {OUTPUT}")

    write_mode = "a" if existing_titles else "w"
    count = len(existing_titles)

    with open(OUTPUT, write_mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_mode == "w":
            writer.writerow(CSV_FIELDS)

        for page in range(1, DISCOVER_PAGES + 1):
            if count >= TARGET:
                break

            print(f"\n-- Discover page {page:02d}/{DISCOVER_PAGES} --")

            try:
                movies = discover_page(page)
            except Exception as exc:
                print(f"  [page error] {exc} — skipping page {page}")
                time.sleep(2)
                continue

            for movie in movies:
                if count >= TARGET:
                    break

                title = movie.get("title", "").strip()

                if title in existing_titles:
                    print(f"  [skip dup ] {title}")
                    continue

                try:
                    full = get_full_movie(movie["id"])
                    row  = build_row(full)
                    writer.writerow(row)
                    csvfile.flush()          # safe write on each row
                    existing_titles.add(title)
                    count += 1
                    print(f"  [{count:4d}/{TARGET}] {title}")
                except Exception as exc:
                    print(f"  [skip err ] {title}: {exc}")

                time.sleep(SLEEP_SEC)

    print(f"\nFinished. {count} movies saved to:\n  {OUTPUT}")


if __name__ == "__main__":
    main()
