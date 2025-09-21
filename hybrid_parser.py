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

DATASET_FILE = "log_query_dataset.csv"
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
def to_spl(parsed):
    action_map = {
        "failure": 'sourcetype=sshd ("Failed password" OR "auth failure")',
        "success": 'sourcetype=sshd ("Accepted password" OR "auth success")',
        "login": 'sourcetype=sshd "session opened"',
        "logout": 'sourcetype=sshd "session closed"',
        "download": 'sourcetype=access_combined action=download',
        "upload": 'sourcetype=access_combined action=upload',
        "error": 'sourcetype=syslog (error OR fail OR exception)',
        "access": 'sourcetype=access_combined',
        "restart": 'sourcetype=syslog ("service restart" OR "system reboot")',
        "deletion": 'sourcetype=fs change=deleted',
        "*": "*"
    }

    time_map = {
        "today": "earliest=@d latest=now",
        "last24h": "earliest=-24h@h latest=now",
        "last7d": "earliest=-7d@d latest=now",
        "last30d": "earliest=-30d@d latest=now",
        "last1h": "earliest=-1h@h latest=now",
        "*": ""
    }

    source_map = {
        "auth": 'index=auth',
        "web": 'index=web',
        "ssh": 'index=ssh',
        "database": 'index=db',
        "filesystem": 'index=fs',
        "host": 'index=host',
        "*": "index=*"
    }

    action_part = action_map.get(parsed["action"], "*")
    time_part = time_map.get(parsed["time"], "")
    source_part = source_map.get(parsed["source"], "index=*")

    user_part = ""
    if parsed["user"] != "*":
        user_part = f'user={parsed["user"]}'

    spl = f'{source_part} {action_part} {user_part} {time_part}'
    return spl.strip()


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


# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    models = train_all()

    force_mode = False
    args = sys.argv[1:]

    if "-f" in args:
        force_mode = True
        args.remove("-f")

    if force_mode:
        print("⚡ Running in force mode: skipping clarification prompts.\n")

    if len(args) > 0:
        nl_query = " ".join(args)
        parsed = predict_query(nl_query, models)
        if not force_mode:
            parsed = clarification_prompt(parsed)
        spl = to_spl(parsed)
        print("\nNL Query:", nl_query)
        print("Hybrid Parsed:", parsed)
        print("Generated SPL:", spl)
    else:
        tests = [
            "show me failed logins from yesterday",
            "list all upload events since yesterday",
            "give me all errors this week",
        ]
        for t in tests:
            parsed = predict_query(t, models)
            if not force_mode:
                parsed = clarification_prompt(parsed)
            spl = to_spl(parsed)
            print("\nNL Query:", t)
            print("Hybrid Parsed:", parsed)
            print("Generated SPL:", spl)

