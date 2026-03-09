# CineMatch — Movie Recommendation Web App

A full-stack movie recommendation application that learns your taste through a short survey and returns 5 personalised picks using **TF-IDF cosine similarity** combined with **IMDB audience sentiment analysis**.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [How It Works](#how-it-works)
5. [Environment Setup](#environment-setup)
6. [Running the App](#running-the-app)
7. [Data Pipeline](#data-pipeline)
8. [Deployment on Render / Railway](#deployment-on-render--railway)
9. [Docker](#docker)

---

## Introduction

CineMatch collects your preferences (favourite actors, directors, genres, and movie titles) through a survey page, then:

- Flattens every movie's metadata into a single string
- Compares it to your preference string using **TF-IDF + cosine similarity**
- Boosts scores with a **VADER sentiment score** derived from real IMDB user reviews
- Returns the top 5 matches you haven't already selected

If you skip the survey, the app falls back to the top-rated movies by TMDB vote average.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend framework | **FastAPI** | REST API + serves frontend static files |
| ASGI server | **Uvicorn** | Runs the FastAPI app |
| Data collection | **requests** + TMDB API | Fetches 1 000 movies with metadata |
| Web scraping | **httpx** + **BeautifulSoup4** | Scrapes IMDB user reviews |
| Sentiment analysis | **VADER** (`vaderSentiment`) | Scores reviews −1.0 → +1.0 |
| Recommendation engine | **scikit-learn** TF-IDF + cosine similarity | Matches user taste to movies |
| Data handling | **pandas** | Reads/writes CSV, numeric coercion |
| Frontend | **Vanilla JS** + **HTML5** + **CSS3** | No build step required |
| Styling | **Tailwind CSS** (CDN) | Responsive dark-theme UI |
| Icons | **Font Awesome** (CDN) | Visual elements |
| Config | **python-dotenv** | Loads TMDB API key from `.env` |

---

## Project Structure

```
Movie-Recommendation-Web/
│
├── .env                        # TMDB_API_KEY (never commit this)
├── fetch_movies.py             # Step 1: collect 1 000 movies → Data/movies_1000.csv
│
├── Data/
│   ├── actors.txt              # Survey list — actor names (one per line)
│   ├── directors.txt           # Survey list — director names
│   ├── genres.txt              # Survey list — genre names
│   ├── movieTitles.txt         # Survey list — movie titles
│   ├── movies_1000.csv         # Raw movie data (generated)
│   └── movies_enriched.csv     # + sentiment_score column (generated)
│
├── backend/
│   ├── main.py                 # FastAPI app, all routes, static file mount
│   ├── recommend.py            # TF-IDF recommendation engine
│   ├── scraper.py              # IMDB review scraper (BS4 + httpx)
│   ├── sentiment.py            # VADER wrapper
│   ├── enrich.py               # One-time script: add sentiment to CSV
│   └── requirements.txt        # All Python dependencies
│
├── frontend/
│   ├── index.html              # Landing page
│   ├── survey.html             # Survey — 4 multi-select listboxes
│   ├── results.html            # Results — 5 movie cards
│   ├── css/style.css           # Custom styles (dark theme, cards, badges)
│   └── js/
│       ├── survey.js           # Load lists from API, submit selections
│       └── results.js          # Fetch recommendations, render cards
│
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Compose for easy local container run
└── README.md                   # This file
```

---

## How It Works

### Survey
The survey page reads four `.txt` files from `Data/` and populates multi-select listboxes.
The user picks any combination of actors, directors, genres, and movie titles.

### Recommendation Algorithm

```
1. Build a "movie string" for every row in the CSV:
      "{title} {year} {genres} {director} {actor1} {actor2} {actor3}"

2. Build a "user string" from all selections:
      "{selected actors} {selected directors} {selected genres} {selected titles}"

3. Vectorise all strings with TF-IDF (stop_words='english')

4. Compute cosine_similarity(user_vector, every_movie_vector)

5. final_score = similarity_score + 0.1 × sentiment_score

6. Exclude movies the user selected in the survey (title match)

7. Return top 5 by final_score
```

**Fallback:** If the user makes no selections, return top 5 by `vote_average`.

### Sentiment Score
`enrich.py` scrapes up to 25 IMDB user reviews per movie via BeautifulSoup4,
runs each through VADER, and averages the compound scores (−1.0 to +1.0).
Movies with no reviews get a neutral score of 0.0.

---

## Environment Setup

### Prerequisites
- Python 3.11+
- pip

### 1. Clone and enter the project
```bash
git clone <repo-url>
cd Movie-Recommendation-Web
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate — Windows CMD
venv\Scripts\activate.bat

# Activate — Windows PowerShell
venv\Scripts\Activate.ps1

# Activate — macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Set your TMDB API key
Create a `.env` file in the project root:
```
TMDB_API_KEY=your_key_here
```
Get a free key at https://www.themoviedb.org/settings/api

---

## Running the App

### Quick start (data already collected)
```bash
uvicorn backend.main:app --reload --port 8000
```
Open **http://localhost:8000** in your browser.

| URL | Page |
|---|---|
| http://localhost:8000 | Landing page |
| http://localhost:8000/survey.html | Take the survey |
| http://localhost:8000/results.html | View recommendations |
| http://localhost:8000/docs | Interactive API docs (FastAPI) |

---

## Data Pipeline

Run these steps once to build the data files.
The server works without `movies_enriched.csv` (sentiment defaults to 0.0).

### Step 1 — Collect 1 000 movies from TMDB
```bash
python fetch_movies.py
```
- Output: `Data/movies_1000.csv`
- Runtime: ~5 minutes (rate-limited at 0.26 s/request)
- Supports resume: re-running skips already-saved titles

### Step 2 — Enrich with IMDB sentiment (optional but recommended)
```bash
python backend/enrich.py
```
- Output: `Data/movies_enriched.csv`
- Runtime: ~30–45 minutes (1.5 s sleep between IMDB requests)
- Supports resume: re-running skips already-enriched titles

---

## Deployment on Render / Railway

### Render (free tier)

1. Push the repo to GitHub
2. Create a new **Web Service** on https://render.com
3. Set:
   - **Build command:** `pip install -r backend/requirements.txt`
   - **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variable: `TMDB_API_KEY=your_key_here`
5. Upload `Data/movies_enriched.csv` (or `movies_1000.csv`) to the repo before deploying

> Render's free tier spins down after inactivity — the first request after sleep takes ~30 s.

### Railway

1. Push repo to GitHub
2. New project → Deploy from GitHub repo
3. Add variable: `TMDB_API_KEY=your_key_here`
4. Railway auto-detects Python and runs the start command:
   ```
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

---

## Docker

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
services:
  cinematch:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TMDB_API_KEY=${TMDB_API_KEY}
    volumes:
      - ./Data:/app/Data     # persist CSV files outside the container
```

### Build and run
```bash
# Build image
docker build -t cinematch .

# Run with env file
docker run --env-file .env -p 8000:8000 cinematch

# Or use Compose
docker compose up --build
```

Open **http://localhost:8000**

### Notes
---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/survey-data` | Returns actors / directors / genres / titles lists |
| `POST` | `/api/recommend` | Returns 5 movie recommendations |

### POST /api/recommend

**Request body:**
```json
{
  "actors":    ["Keanu Reeves"],
  "directors": ["Christopher Nolan"],
  "genres":    ["Action", "Sci-Fi"],
  "titles":    ["Interstellar"]
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "movie_title":      "Inception",
      "release_year":     "2010",
      "genres":           "Action, Adventure, Science Fiction",
      "director_name":    "Christopher Nolan",
      "actor_1_name":     "Leonardo DiCaprio",
      "vote_average":     8.8,
      "sentiment_score":  0.72,
      "similarity_score": 0.46,
      "poster_url":       "https://image.tmdb.org/t/p/w500/..."
    }
  ]
}
```

---

## Notes

- **IMDB scraping** respects a 1.5 s delay between requests. If IMDB blocks the scraper, `enrich.py` automatically falls back to TMDB's own `/movie/{id}/reviews` endpoint.
- **Data files** (`movies_1000.csv`, `movies_enriched.csv`) are not committed to git. Add them to `.gitignore`:
  ```
  .env
  Data/movies_1000.csv
  Data/movies_enriched.csv
  venv/
  __pycache__/
  ```
- **Re-collecting data** after the TMDB API key changes: delete the CSV and re-run `fetch_movies.py`.
