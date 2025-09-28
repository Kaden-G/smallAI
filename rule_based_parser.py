#!/usr/bin/env python3
import os
import re
import csv
import sys

# Always resolve dataset relative to this script’s folder
BASE_DIR = os.path.dirname(__file__)
DATASET_FILE = os.path.join(BASE_DIR, "log_query_dataset.csv")

# -------------------------------
# Keyword dictionaries
# -------------------------------
action_keywords = {
    "error": ["error", "crash", "problem", "failure"],
    "download": ["download", "file download"],
    "upload": ["upload", "file upload"],
    "access": ["access", "connection", "request"],
    "restart": ["restart", "service restart"],
    "deletion": ["delete", "removed", "file deletion"],
}

time_keywords = {
    "today": ["today", "since midnight", "in the last 24 hours"],
    "yesterday": ["yesterday", "the previous day"],
    "last7d": ["last 7 days", "this week", "past week"],
    "last30d": ["last 30 days", "this month"],
    "last1h": ["last hour", "past 60 minutes"],
    "last24h": ["last 24 hours", "since yesterday", "past 24 hours", "last day"],
}

source_keywords = {
    "auth": ["auth log", "authentication log", "security log"],
    "web": ["web", "web server", "nginx", "apache"],
    "ssh": ["ssh", "secure shell"],
    "database": ["database", "db"],
    "filesystem": ["filesystem", "file system"],
    "host": ["host", "server", "machine"],
}

users = ["root", "alice", "bob", "jsmith", "admin", "anonymous"]

def parse_query(nl_query: str):
    text = nl_query.lower()
    parsed = {"action": "*", "time": "*", "user": "*", "source": "*"}

    # Action extraction
    if re.search(r"failed login|login failure|auth failure", text):
        parsed["action"] = "failure"
    elif re.search(r"successful login|auth success", text):
        parsed["action"] = "success"
    elif re.search(r"\blogin(s)?\b", text) and "upload" not in text:
        parsed["action"] = "login"
    elif re.search(r"\blogout(s)?\b|sign off", text):
        parsed["action"] = "logout"
    elif re.search(r"authentication|authenticating|auth event", text):
        parsed["action"] = "login"
    else:
        for act, keywords in action_keywords.items():
            if any(kw in text for kw in keywords):
                parsed["action"] = act
                break

    # Time extraction
    if re.search(r"since yesterday|past day|last day", text):
        parsed["time"] = "last24h"
    else:
        for t, keywords in time_keywords.items():
            if any(kw in text for kw in keywords):
                parsed["time"] = t
                break

    # User extraction
    for u in users:
        if re.search(rf"\b{u}\b", text):
            parsed["user"] = u
            break

    # Source extraction
    for s, keywords in source_keywords.items():
        if any(kw in text for kw in keywords):
            parsed["source"] = s
            break

    return parsed

# Wrapper so hybrid_parser can import the expected function
def parse_rule_based(query: str) -> dict:
    return parse_query(query)

def structured_string(parsed: dict):
    parts = [f"action={parsed['action']}"]
    if parsed["time"] != "*":
        parts.append(f"time={parsed['time']}")
    if parsed["user"] != "*":
        parts.append(f"user={parsed['user']}")
    if parsed["source"] != "*":
        parts.append(f"source={parsed['source']}")
    return " ".join(parts)

def evaluate(dataset=DATASET_FILE, show_fails=10):
    with open(dataset, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    exact = 0
    field_correct = {"action": 0, "time": 0, "user": 0, "source": 0}
    failures = []

    for row in rows:
        parsed = parse_query(row["nl_query"])
        predicted = structured_string(parsed)
        gold = row["structured_query"]

        if predicted == gold:
            exact += 1
        else:
            if len(failures) < show_fails:
                failures.append({
                    "nl_query": row["nl_query"],
                    "predicted": predicted,
                    "gold": gold
                })

        for field in field_correct:
            if parsed[field] == row[field]:
                field_correct[field] += 1

    print(f"Evaluated {total} queries")
    print(f"Exact matches: {exact} / {total} = {exact/total:.2%}")
    print("\nPer-field accuracy:")
    for field, correct in field_correct.items():
        print(f"  {field:6s}: {correct} / {total} = {correct/total:.2%}")

    if failures:
        print("\nExamples of failed cases:")
        for f in failures:
            print(f"- NL: {f['nl_query']}")
            print(f"  Predicted: {f['predicted']}")
            print(f"  Gold:      {f['gold']}\n")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        nl_query = sys.argv[1]
        parsed = parse_query(nl_query)
        print("NL Query:", nl_query)
        print("Parsed:", structured_string(parsed))
    else:
        evaluate()
