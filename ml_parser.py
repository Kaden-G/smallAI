#!/usr/bin/env python3


"""
ml_parser.py
------------
Machine learning parser for natural language → Splunk SPL slot filling.

- Loads dataset of NL queries and labeled slots
- Trains per-slot classifiers (action, time, user, source)
- Predicts slot values for a new query
"""

from __future__ import annotations

import csv
import os
import random
from typing import List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------
# Dataset path resolution (always points to smallAI/datasets/log_query_dataset.csv)
# ---------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))  # this file = smallAI/ml_parser.py
DATASET_FILE = os.path.join(REPO_ROOT, "datasets", "log_query_dataset.csv")


def load_dataset(filename: Optional[str] = None) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    """
    Load the training dataset of natural language queries and slot labels.
    Returns:
        X: list of NL queries
        y_action, y_time, y_user, y_source: labels for each slot
    """
    path = filename or DATASET_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at {path}. Ensure datasets/log_query_dataset.csv exists under project root."
        )

    X, y_action, y_time, y_user, y_source = [], [], [], [], []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            X.append(r["nl_query"].lower())  # normalize text to lowercase
            y_action.append(r["action"])
            y_time.append(r["time"])
            y_user.append(r["user"])
            y_source.append(r["source"])
    return X, y_action, y_time, y_user, y_source


def train_classifier(X: List[str], y: List[str]) -> Pipeline:
    """
    Train a single slot classifier using TF-IDF + Logistic Regression.
    """
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=3000)),
        ("clf", LogisticRegression(max_iter=1000))
    ])
    pipe.fit(X, y)
    return pipe


def train_all(filename: Optional[str] = None) -> Tuple[Pipeline, Pipeline, Pipeline, Pipeline]:
    """
    Train all four classifiers (action, time, user, source).
    Returns a tuple of sklearn Pipelines.
    """
    X, y_action, y_time, y_user, y_source = load_dataset(filename)

    # Shuffle for randomness
    combined = list(zip(X, y_action, y_time, y_user, y_source))
    random.shuffle(combined)
    Xs, a, t, u, s = zip(*combined)

    clf_a = train_classifier(list(Xs), list(a))
    clf_t = train_classifier(list(Xs), list(t))
    clf_u = train_classifier(list(Xs), list(u))
    clf_s = train_classifier(list(Xs), list(s))
    return clf_a, clf_t, clf_u, clf_s


def predict_query(q: str, clf_a: Pipeline, clf_t: Pipeline, clf_u: Pipeline, clf_s: Pipeline) -> dict:
    """
    Predict slot values for a given natural language query.
    """
    return {
        "action": clf_a.predict([q.lower()])[0],
        "time": clf_t.predict([q.lower()])[0],
        "user": clf_u.predict([q.lower()])[0],
        "source": clf_s.predict([q.lower()])[0],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("Training classifiers...")
        train_all()
        print("Done")
    else:
        models = train_all()
        q = " ".join(sys.argv[1:])
        print("Query:", q)
        print("Prediction:", predict_query(q, *models))
