"""
scraper.py
----------
Scrapes user reviews from IMDB for a given IMDB ID using httpx + BeautifulSoup4.
Falls back to TMDB's own review endpoint if IMDB blocks the request.
"""

import os
import sys
import time

import httpx
from bs4 import BeautifulSoup

# TMDB fallback needs the API key
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE    = "https://api.themoviedb.org/3"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _scrape_imdb(imdb_id: str, max_reviews: int) -> list[str]:
    """Try to scrape IMDB review page directly."""
    url = f"https://www.imdb.com/title/{imdb_id}/reviews"
    with httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Current IMDB layout (2024+)
    divs = soup.select("div.ipc-html-content-inner-div")
    if not divs:
        # Older IMDB layout fallback
        divs = soup.select("div.text.show-more__control")

    return [d.get_text(separator=" ", strip=True) for d in divs[:max_reviews]]


def _tmdb_reviews(imdb_id: str, max_reviews: int) -> list[str]:
    """Fallback: fetch reviews from TMDB using the movie's TMDB ID lookup."""
    if not TMDB_API_KEY:
        return []
    try:
        # First resolve imdb_id → tmdb movie_id via /find
        find_url = f"{TMDB_BASE}/find/{imdb_id}"
        resp = httpx.get(
            find_url,
            params={"api_key": TMDB_API_KEY, "external_source": "imdb_id"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("movie_results", [])
        if not results:
            return []
        tmdb_id = results[0]["id"]

        # Fetch TMDB reviews
        reviews_url = f"{TMDB_BASE}/movie/{tmdb_id}/reviews"
        resp = httpx.get(reviews_url, params={"api_key": TMDB_API_KEY}, timeout=10)
        resp.raise_for_status()
        reviews = resp.json().get("results", [])
        return [r["content"] for r in reviews[:max_reviews]]
    except Exception:
        return []


def scrape_reviews(imdb_id: str, max_reviews: int = 25) -> list[str]:
    """
    Return up to max_reviews user review texts for the given IMDB ID.
    Tries IMDB directly first; falls back to TMDB reviews on any error.
    Returns an empty list if both sources fail.
    """
    if not imdb_id:
        return []
    try:
        reviews = _scrape_imdb(imdb_id, max_reviews)
        if reviews:
            return reviews
    except Exception:
        pass

    # Fallback
    return _tmdb_reviews(imdb_id, max_reviews)
