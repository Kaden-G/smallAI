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
import joblib
from pathlib import Path
from typing import List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------
# Dataset path resolution (always points to smallAI/datasets/train_queries.csv)
# ---------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # this file = smallAI/src/ml_parser.py
DATASET_FILE = os.path.join(REPO_ROOT, "datasets", "train_queries.csv")

# ---------------------------------------------------------------------
# Model Configuration Block
# ---------------------------------------------------------------------
MODEL_DIR = Path(REPO_ROOT) / "models"
SLOTS = [
    "action", "time", "user", "source",
    "src_ip", "hostname", "severity", "status_code",
]
MODEL_VERSION = "slot_models_v1"

# Load vectorizer and slot models (lazy loading)
_vectorizer = None
_slot_models = None

def _load_models():
    """Lazy load vectorizer and slot models."""
    global _vectorizer, _slot_models

    if _vectorizer is not None and _slot_models is not None:
        return _vectorizer, _slot_models

    vectorizer_path = MODEL_DIR / "vectorizer.pkl"
    if not vectorizer_path.exists():
        # Models not trained yet, return None
        return None, None

    _vectorizer = joblib.load(vectorizer_path)
    _slot_models = {}

    for slot in SLOTS:
        path = MODEL_DIR / f"model_{slot}.pkl"
        if path.exists():
            _slot_models[slot] = joblib.load(path)
        else:
            print(f"[WARN] No model found for slot '{slot}' — skipping.")

    return _vectorizer, _slot_models


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
            f"Dataset not found at {path}. Ensure datasets/train_queries.csv exists under project root."
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


def parse_ml(query: str) -> dict:
    """
    Predict slot values for a given natural language query using pre-trained models.

    This function uses the models trained by scripts/train_ml_parser.py.
    If models are not found, it falls back to training in-memory.

    Args:
        query: Natural language query string

    Returns:
        Dict with predicted slot values for all 8 slots
    """
    if not query or not query.strip():
        return {slot: None for slot in SLOTS}

    vectorizer, slot_models = _load_models()

    # If models don't exist, fall back to in-memory training
    if vectorizer is None or slot_models is None:
        print("[INFO] Pre-trained models not found. Training in-memory...")
        classifiers = train_all()
        return predict_query(query, classifiers)

    # Use pre-trained models
    X_vec = vectorizer.transform([query])
    results = {}

    for slot, model in slot_models.items():
        try:
            pred = model.predict(X_vec)[0]
            if not pred or pred.lower() in ["none", "null", "nan", ""]:
                pred = None
            results[slot] = pred
        except Exception as e:
            print(f"[WARN] Prediction failed for slot '{slot}': {e}")
            results[slot] = None

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("Usage: python ml_parser.py \"<query>\"")
        print("Example: python ml_parser.py \"show failed logins from yesterday\"")
        sys.exit(0)

    q = " ".join(sys.argv[1:])
    print("Query:", q)
    print("Prediction:", parse_ml(q))
