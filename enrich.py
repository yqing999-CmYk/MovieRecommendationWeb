#!/usr/bin/env python3
"""
enrich.py
---------
One-time script that reads Data/movies_1000.csv, scrapes IMDB reviews for
each movie, runs VADER sentiment analysis, and writes Data/movies_enriched.csv.

Run from the project root:
    python backend/enrich.py

Supports resuming: already-processed movies are skipped on re-run.
Expected runtime: ~30-45 min for 1000 movies (1.5 s sleep between requests).
"""

import csv
import os
import sys
import time

# Make backend-local imports work when run as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper   import scrape_reviews
from sentiment import average_score

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE  = os.path.join(_ROOT, "Data", "movies_1000.csv")
OUTPUT_FILE = os.path.join(_ROOT, "Data", "movies_enriched.csv")
SLEEP_SEC   = 1.5   # polite delay between IMDB requests


def main() -> None:
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found.\nRun fetch_movies.py first.")
        sys.exit(1)

    # ── Resume: collect titles already in output ─────────────────────────────
    done: set[str] = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done.add(row.get("movie_title", "").strip())
        print(f"Resuming — {len(done)} movies already enriched.")
    else:
        print("Starting fresh enrichment run.")

    # ── Open input and output ────────────────────────────────────────────────
    with open(INPUT_FILE, encoding="utf-8") as infile:
        reader    = csv.DictReader(infile)
        in_fields = reader.fieldnames or []
        out_fields = in_fields + (
            ["sentiment_score"] if "sentiment_score" not in in_fields else []
        )

        mode = "a" if done else "w"
        with open(OUTPUT_FILE, mode, newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=out_fields)
            if mode == "w":
                writer.writeheader()

            rows  = list(reader)
            total = len(rows)

            for i, row in enumerate(rows, start=1):
                title   = row.get("movie_title", "").strip()
                imdb_id = row.get("imdb_id",     "").strip()

                if title in done:
                    continue

                if not imdb_id:
                    row["sentiment_score"] = 0.0
                    label = "(no imdb_id)"
                else:
                    reviews = scrape_reviews(imdb_id)
                    score   = round(average_score(reviews), 4)
                    row["sentiment_score"] = score
                    label = f"{len(reviews)} reviews → score {score:+.4f}"
                    time.sleep(SLEEP_SEC)

                writer.writerow(row)
                outfile.flush()
                done.add(title)
                print(f"[{i:4d}/{total}] {title} — {label}")

    print(f"\nDone. Enriched CSV saved to:\n  {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
