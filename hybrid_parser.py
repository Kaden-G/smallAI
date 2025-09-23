#!/usr/bin/env python3
"""
Hybrid Log Query Parser with Splunk SPL Generator
-------------------------------------------------
- ML-first with rule fallback.
- Normalizes time fields.
- Generates realistic Splunk SPL queries.
- Prompts the user if key fields (source, user) are missing.
- Supports `-f` (force mode) to skip prompts and keep wildcards.
"""

import csv
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np
import rule_based_parser as rb

DATASET_FILE = "datasets/log_query_dataset.csv"
CONF_THRESHOLD = 0.7

# -------------------------------
# Load dataset
# -------------------------------
def load_dataset(filename=DATASET_FILE):
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = [row["nl_query"].lower() for row in rows]
    y_action = [row["action"] for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source


# -------------------------------
# Train classifiers
# -------------------------------
def train_classifier(X, y):
    clf = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("lr", LogisticRegression(max_iter=200))
    ])
    clf.fit(X, y)
    return clf


def train_all():
    X, y_action, y_time, y_user, y_source = load_dataset()
    return {
        "action": train_classifier(X, y_action),
        "time": train_classifier(X, y_time),
        "user": train_classifier(X, y_user),
        "source": train_classifier(X, y_source),
    }


# -------------------------------
# Normalization
# -------------------------------
def normalize_slots(parsed):
    if parsed.get("time") == "yesterday":
        parsed["time"] = "last24h"
    return parsed


# -------------------------------
# Clarification prompt (CLI)
# -------------------------------
def clarification_prompt(parsed):
    # If source missing
    if parsed.get("source") == "*":
        options = ["auth", "ssh", "web", "database", "filesystem", "host"]
        print("\nMissing field: source")
        for i, opt in enumerate(options, 1):
            print(f"[{i}] {opt}")
        print("[0] I don't know (keep *)")
        choice = input("Choose a source: ").strip()
        if choice.isdigit() and int(choice) in range(1, len(options) + 1):
            parsed["source"] = options[int(choice) - 1]
        else:
            parsed["source"] = "*"  # keep wildcard

    # If user missing
    if parsed.get("user") == "*":
        options = ["root", "admin", "bob", "alice", "anonymous"]
        print("\nMissing field: user")
        for i, opt in enumerate(options, 1):
            print(f"[{i}] {opt}")
        print("[0] I don't know (keep *)")
        choice = input("Choose a user: ").strip()
        if choice.isdigit() and int(choice) in range(1, len(options) + 1):
            parsed["user"] = options[int(choice) - 1]
        else:
            parsed["user"] = "*"  # keep wildcard

    return parsed


# -------------------------------
# SPL generator

# -------------------------------
# SPL generator (sourcetype-aware)
# -------------------------------
def to_spl(parsed):
    """
    Build an SPL query using Splunk-native sourcetypes.
    Preference order:
      1) If parsed["source"] is already a Splunk sourcetype we know (access_combined, syslog, errors_demo), use it.
      2) Otherwise map high-level sources (auth/web/host/filesystem/database/ssh) to the closest sourcetype.
      3) Fallback to "*" if unknown.
    Index: default to "main" for demo purposes, since uploads went to main.
    """
    # Known sourcetypes used in your Splunk demo
    known_sourcetypes = {"access_combined", "syslog", "errors_demo"}

    # Map high-level sources → Splunk sourcetypes
    source_to_sourcetype = {
        "auth": "syslog",
        "ssh": "syslog",
        "web": "access_combined",
        "host": "errors_demo",
        "filesystem": "errors_demo",
        "database": "errors_demo",
        "*": "*",
    }

    # Action templates (no sourcetype baked in)
    action_templates = {
        "failure": '("Failed password" OR "auth failure")',
        "success": '("Accepted password" OR "auth success")',
        "login": '"session opened"',
        "logout": '"session closed"',
        "download": 'action=download',
        "upload": 'action=upload',
        "error": '(error OR fail OR exception)',
        "access": '',
        "restart": '("service restart" OR "system reboot")',
        "deletion": 'change=deleted',
        "*": "",
    }

    time_map = {
        "today": "earliest=@d latest=now",
        "last24h": "earliest=-24h@h latest=now",
        "last7d": "earliest=-7d@d latest=now",
        "last30d": "earliest=-30d@d latest=now",
        "last1h": "earliest=-1h@h latest=now",
        "*": "",
    }

    # Determine sourcetype
    src = parsed.get("source", "*")
    if src in known_sourcetypes:
        st = src
    else:
        st = source_to_sourcetype.get(src, "*")

    # Build SPL parts
    parts = []
    parts.append("index=main")  # your uploads went to main
    if st != "*":
        parts.append(f"sourcetype={st}")

    action_clause = action_templates.get(parsed.get("action", "*"), "")
    if action_clause:
        parts.append(action_clause)

    user = parsed.get("user", "*")
    if user and user != "*":
        parts.append(f'user={user}')

    time_clause = time_map.get(parsed.get("time", "*"), "")
    if time_clause:
        parts.append(time_clause)

    return " ".join(parts).strip()


# -------------------------------
# Hybrid prediction
# -------------------------------
def predict_query(query, models, threshold=CONF_THRESHOLD):
    query = query.lower()
    result = {}
    rb_parsed = rb.parse_query(query)

    for slot, clf in models.items():
        proba = clf.predict_proba([query])[0]
        pred_idx = np.argmax(proba)
        pred_label = clf.classes_[pred_idx]
        confidence = proba[pred_idx]

        if confidence >= threshold:
            result[slot] = pred_label
        else:
            result[slot] = rb_parsed[slot]

    result = normalize_slots(result)
    return result

from sklearn.metrics import accuracy_score

def evaluate_all():
    X, y_action, y_time, y_user, y_source = load_dataset()
    models = train_all()
    y_pred_action = models["action"].predict(X)
    y_pred_time = models["time"].predict(X)
    y_pred_user = models["user"].predict(X)
    y_pred_source = models["source"].predict(X)

    print("\n=== Evaluation Results ===")
    print(f"Action accuracy:     {accuracy_score(y_action, y_pred_action) * 100:.2f}%")
    print(f"Time accuracy:       {accuracy_score(y_time, y_pred_time) * 100:.2f}%")
    print(f"User accuracy:       {accuracy_score(y_user, y_pred_user) * 100:.2f}%")
    print(f"Sourcetype accuracy: {accuracy_score(y_source, y_pred_source) * 100:.2f}%")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    force_mode = False
    args = sys.argv[1:]

    if "-f" in args:
        force_mode = True
        args.remove("-f")

    if force_mode:
        print("⚡ Running in force mode: skipping clarification prompts.\n")

    if len(args) > 0:
        # parse a single natural-language query
        models = train_all()
        nl_query = " ".join(args)
        parsed = predict_query(nl_query, models)
        if not force_mode:
            parsed = clarification_prompt(parsed)
        spl = to_spl(parsed)
        print("\nNL Query:", nl_query)
        print("Hybrid Parsed:", parsed)
        print("Generated SPL:", spl)
    else:
        # no args → run evaluation on the dataset
        evaluate_all()
