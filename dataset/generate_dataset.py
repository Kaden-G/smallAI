#!/usr/bin/env python3
import csv
import random
import datetime

# Synonyms for "show me"
query_prefixes = [
    "show me", "list", "find", "display", "give me", "pull up"
]

actions = {
    "login": ["login", "logins", "authentication"],
    "failure": ["failed login", "login failure", "auth failure"],
    "success": ["successful login", "auth success"],
    "download": ["download", "file download"],
    "upload": ["upload", "file upload"],
    "error": ["error", "failure", "crash"],
    "access": ["access", "connection", "request"],
    "logout": ["logout", "sign off"],
    "restart": ["restart", "service restart"],
    "deletion": ["delete", "file deletion"],
}

times = {
    "today": ["today", "since midnight", "in the last 24 hours"],
    "yesterday": ["yesterday", "the previous day"],
    "last7d": ["last 7 days", "this week", "past week"],
    "last30d": ["last 30 days", "this month"],
    "last1h": ["last hour", "past 60 minutes"],
    "last24h": ["last 24 hours", "since yesterday"],
}

users = ["*", "root", "alice", "bob", "jsmith", "admin", "anonymous"]

sources = {
    "auth": ["auth log", "authentication log", "security log"],
    "web": ["web server", "nginx", "apache"],
    "ssh": ["ssh", "secure shell"],
    "database": ["database", "db"],
    "filesystem": ["filesystem", "file system"],
    "host": ["host", "server", "machine"],
}

def map_time_to_bounds(time_slot: str) -> str:
    mapping = {
        "last1h": 'earliest=-60m latest=now',
        "last24h": 'earliest=-24h latest=now',
        "last30d": 'earliest=-30d@d latest=now',
        "yesterday": 'earliest=@d-1d latest=@d',
        "today": 'earliest=@d latest=now',
        "last7d": 'earliest=-7d@d latest=now',
    }
    return mapping.get(time_slot.lower(), f'time={time_slot}')

def generate_event_ts(time_key: str) -> str:
    """Generate a realistic event timestamp string based on the time slot."""
    now = datetime.datetime.now()
    if time_key == "last1h":
        dt = now - datetime.timedelta(minutes=random.randint(0, 59))
    elif time_key == "last24h":
        dt = now - datetime.timedelta(hours=random.randint(0, 23))
    elif time_key == "yesterday":
        yesterday = now - datetime.timedelta(days=1)
        dt = yesterday.replace(hour=random.randint(0, 23), minute=random.randint(0, 59))
    elif time_key == "today":
        dt = now.replace(hour=random.randint(0, now.hour), minute=random.randint(0, 59))
    elif time_key == "last7d":
        dt = now - datetime.timedelta(days=random.randint(0, 6))
    elif time_key == "last30d":
        dt = now - datetime.timedelta(days=random.randint(0, 29))
    else:
        dt = now
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")

def generate_structured(action_key, time_key, user, source_key):
    parts = []
    parts.append(f"action={action_key}")
    if user != "*":
        parts.append(f"user={user}")
    if source_key != "*":
        parts.append(f"source={source_key}")
    if time_key != "*":
        parts.append(map_time_to_bounds(time_key))
    return " ".join(parts)

def generate_queries(n=480):
    rows = []
    for _ in range(n):
        prefix = random.choice(query_prefixes)
        action_key = random.choice(list(actions.keys()))
        action_phrase = random.choice(actions[action_key])
        time_key = random.choice(list(times.keys()))
        time_phrase = random.choice(times[time_key])
        user = random.choice(users)
        source_key = random.choice(list(sources.keys()))
        source_phrase = random.choice(sources[source_key])

        # Construct natural language query
        user_part = "" if user == "*" else f" by user {user}"
        nl_query = f"{prefix} all {action_phrase} events{user_part} {time_phrase} in {source_phrase}"

        structured = generate_structured(action_key, time_key, user, source_key)
        event_ts = generate_event_ts(time_key)

        rows.append([nl_query, action_key, time_key, user, source_key, structured, event_ts])
    return rows

def fixed_gold_examples():
    gold = [
        ["show me failed logins from yesterday", "failure", "yesterday", "*", "auth", "action=failure source=auth earliest=@d-1d latest=@d", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")],
        ["list all successful logins in the last 7 days", "success", "last7d", "*", "auth", "action=success source=auth earliest=-7d@d latest=now", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")],
    ]
    return gold

def save_dataset(filename="log_query_dataset.csv"):
    rows = generate_queries()
    rows.extend(fixed_gold_examples())
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["nl_query", "action", "time", "user", "source", "structured_query", "event_ts"])
        writer.writerows(rows)
    print(f"Saved {len(rows)} examples to {filename}")

if __name__ == "__main__":
    save_dataset()