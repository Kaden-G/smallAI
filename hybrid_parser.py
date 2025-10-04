#!/usr/bin/env python3
"""
Hybrid Parser for converting natural language queries into structured Splunk SPL queries.
Uses a combination of ML predictions and rule-based parsing for robust, explainable results.
"""

import re
import sys

# Use a wildcard index for general deployment (instead of a specific index like "smallai").
DEFAULT_INDEX = "*"

def ml_predict_slots(query):
    """
    Dummy ML model prediction for query slots.
    Replace with real ML model inference later.
    """
    return {}

def normalize_text(query):
    return query.strip()

def parse_natural_language(query):
    q = normalize_text(query)
    slots = {"user": None, "action": None, "source": None, "time": None}

    # Rule-based extraction for user
    user_match = re.search(r'\buser\s+([A-Za-z0-9._-]+)', q, flags=re.IGNORECASE)
    if user_match:
        slots["user"] = user_match.group(1)
    else:
        poss_match = re.search(r"\b([A-Za-z0-9._-]+)'s\b", q, flags=re.IGNORECASE)
        if poss_match:
            slots["user"] = poss_match.group(1)

    # Rule-based extraction for source
    src_match = re.search(r'\bin\s+([A-Za-z0-9._ -]+)$', q, flags=re.IGNORECASE)
    if src_match:
        src_phrase = src_match.group(1).strip().lower()
        if "nginx" in src_phrase or "web" in src_phrase:
            slots["source"] = "web"
        elif "auth" in src_phrase:
            slots["source"] = "auth"
        elif "host" in src_phrase:
            slots["source"] = "host"
        elif "filesystem" in src_phrase or "file system" in src_phrase:
            slots["source"] = "filesystem"
        elif "database" in src_phrase:
            slots["source"] = "database"
        else:
            slots["source"] = src_phrase

    # Rule-based extraction for time
    time_phrases = {
        "last hour": "last1h",
        "last 1 hour": "last1h",
        "last 24 hours": "last24h",
        "last day": "last24h",
        "last 30 days": "last30d",
        "last month": "last30d",
        "past 60 minutes": "last1h",
        "yesterday": "yesterday",
        "today": "today",
        "since midnight": "today",
        "past 48 hours": "last48h",
    }
    for phrase, code in time_phrases.items():
        if phrase in q.lower():
            slots["time"] = code
            break

    # Rule-based extraction for action
    action_map = {
        "login": "login",
        "logins": "login",
        "logout": "logout",
        "sign off": "logout",
        "failed login": "failure",
        "failed logins": "failure",
        "failure": "failure",
        "error": "error",
        "errors": "error",
        "upload": "upload",
        "download": "download",
        "access": "access",
        "connection": "connection",
        "connections": "connection",
    }
    for key, val in action_map.items():
        if key in q.lower():
            slots["action"] = val
            break

    # Merge ML predictions (placeholder for now)
    ml_slots = ml_predict_slots(q)
    for k, v in ml_slots.items():
        if not slots.get(k):
            slots[k] = v

    # Default user → wildcard instead of a name
    if slots["user"] is None:
        slots["user"] = "*"

    return slots

def generate_spl_query(slots):
    spl = f'search index={DEFAULT_INDEX}'
    if slots.get("source"):
        spl += f' source="{slots["source"]}"'
    if slots.get("user") and slots["user"] not in (None, "*"):
        spl += f' user="{slots["user"]}"'
    if slots.get("action"):
        spl += f' action="{slots["action"]}"'

    if slots.get("time"):
        time_map = {
            "last1h": "-1h",
            "last24h": "-24h",
            "last30d": "-30d",
            "last48h": "-48h",
            "yesterday": "-1d@d",
            "today": "@d"
        }
        if slots["time"] in time_map:
            spl += f' earliest={time_map[slots["time"]]}'

    return spl

def main():
    if len(sys.argv) < 2:
        print("Usage: ./hybrid_parser.py \"<natural language query>\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    slots = parse_natural_language(query)
    spl = generate_spl_query(slots)

    print("Input:", query)
    print("Parsed Slots:", slots)
    print("SPL:", spl)

if __name__ == "__main__":
    main()
