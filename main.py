"""
main.py
-------
FastAPI application.  All API routes are prefixed with /api so the
frontend static files can be served from the root without conflicts.

Start the server from the project root:
    uvicorn backend.main:app --reload --port 8000

Then open:  http://localhost:8000
API docs:   http://localhost:8000/docs
"""

import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from recommend import recommend as get_recommendations

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "Movie Recommendation API",
    description = "TF-IDF + sentiment-boosted movie recommendations",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── Paths ──────────────────────────────────────────────────────────────────────

_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_ROOT, "Data")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
PLACEHOLDER_IMG = "https://placehold.co/500x750/1a1a2e/e94560?text=No+Poster"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_txt(filename: str) -> list[str]:
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        # Deduplicate while preserving order
        seen, items = set(), []
        for line in f:
            val = line.strip()
            if val and val not in seen:
                seen.add(val)
                items.append(val)
        return items


def _add_poster_url(record: dict) -> dict:
    poster = record.get("poster_path", "")
    record["poster_url"] = (
        f"{TMDB_IMAGE_BASE}{poster}" if poster else PLACEHOLDER_IMG
    )
    return record


# ── Models ─────────────────────────────────────────────────────────────────────

class SurveyInput(BaseModel):
    actors:    list[str] = []
    directors: list[str] = []
    genres:    list[str] = []
    titles:    list[str] = []


# ── API routes ─────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["util"])
def health():
    return {"status": "ok"}


@app.get("/api/survey-data", tags=["survey"])
def survey_data():
    """Return the four lists used to populate the survey listboxes."""
    return {
        "actors":    _read_txt("actors.txt"),
        "directors": _read_txt("directors.txt"),
        "genres":    _read_txt("genres.txt"),
        "titles":    _read_txt("movieTitles.txt"),
    }


@app.post("/api/recommend", tags=["recommend"])
def recommend(body: SurveyInput):
    """
    Accept user survey selections and return 5 recommended movies.
    Falls back to top-rated movies when no selections are provided.
    """
    try:
        results = get_recommendations(
            actors    = body.actors,
            directors = body.directors,
            genres    = body.genres,
            titles    = body.titles,
        )
        results = [_add_poster_url(r) for r in results]
        return {"recommendations": results}

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code = 503,
            detail      = str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code = 500,
            detail      = f"Recommendation error: {exc}",
        )


# ── Serve frontend as static files ────────────────────────────────────────────
# Must be mounted AFTER all API routes so /api/* routes take priority.

_FRONTEND = os.path.join(_ROOT, "frontend")
if os.path.isdir(_FRONTEND):
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="static")
