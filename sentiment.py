"""
sentiment.py
------------
Thin wrapper around VADER for movie review sentiment scoring.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score(text: str) -> float:
    """Return VADER compound score for a single text in [-1.0, 1.0]."""
    return _analyzer.polarity_scores(text)["compound"]


def average_score(texts: list[str]) -> float:
    """Return the mean compound score across a list of texts.
    Returns 0.0 if the list is empty.
    """
    if not texts:
        return 0.0
    return sum(score(t) for t in texts) / len(texts)
