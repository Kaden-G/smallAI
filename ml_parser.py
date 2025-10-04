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
from typing import List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------
# Dataset path resolution (always points to smallAI/datasets/log_query_dataset.csv)
# ---------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))  # this file = smallAI/ml_parser.py
DATASET_FILE = os.path.join(REPO_ROOT, "datasets", "log_query_dataset.csv")


def load_dataset(filename: Optional[str] = None):
    """
    Load the training dataset of natural language queries and slot labels.
    Returns:
        X: list of NL queries
        y_dict: dict with keys for each slot (action, time, user, source, src_ip, hostname, severity, status_code)
    """
    path = filename or DATASET_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at {path}. Ensure datasets/log_query_dataset.csv exists under project root."
        )

    X = []
    y_dict = {
        "action": [],
        "time": [],
        "user": [],
        "source": [],
        "src_ip": [],
        "hostname": [],
        "severity": [],
        "status_code": []
    }

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            X.append(r["nl_query"].lower())  # normalize text to lowercase
            y_dict["action"].append(r["action"])
            y_dict["time"].append(r["time"])
            y_dict["user"].append(r["user"])
            y_dict["source"].append(r["source"])
            y_dict["src_ip"].append(r["src_ip"])
            y_dict["hostname"].append(r["hostname"])
            y_dict["severity"].append(r["severity"])
            y_dict["status_code"].append(r["status_code"])

    return X, y_dict


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


def train_all(filename: Optional[str] = None):
    """
    Train all eight classifiers (action, time, user, source, src_ip, hostname, severity, status_code).
    Returns a dict of sklearn Pipelines.
    """
    X, y_dict = load_dataset(filename)

    # Shuffle for randomness
    indices = list(range(len(X)))
    random.shuffle(indices)

    X_shuffled = [X[i] for i in indices]
    y_shuffled = {key: [vals[i] for i in indices] for key, vals in y_dict.items()}

    # Train one classifier per slot
    classifiers = {}
    for slot_name in ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]:
        classifiers[slot_name] = train_classifier(X_shuffled, y_shuffled[slot_name])

    return classifiers


def predict_query(q: str, classifiers: dict) -> dict:
    """
    Predict slot values for a given natural language query.

    Args:
        q: Natural language query
        classifiers: Dict of trained Pipeline objects, one per slot

    Returns:
        Dict with predicted slot values
    """
    q_lower = q.lower()
    predictions = {}

    for slot_name, clf in classifiers.items():
        predictions[slot_name] = clf.predict([q_lower])[0]

    return predictions


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("Training classifiers...")
        train_all()
        print("Done")
    else:
        classifiers = train_all()
        q = " ".join(sys.argv[1:])
        print("Query:", q)
        print("Prediction:", predict_query(q, classifiers))
