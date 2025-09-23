#!/usr/bin/env python3
import csv
import random

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

def generate_structured(action_key, time_key, user, source_key):
    parts = []
    parts.append(f"action={action_key}")
    if time_key != "*":
        parts.append(f"time={time_key}")
    if user != "*":
        parts.append(f"user={user}")
    if source_key != "*":
        parts.append(f"source={source_key}")
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

        rows.append([nl_query, action_key, time_key, user, source_key, structured])
    return rows

def fixed_gold_examples():
    gold = [
        ["show me failed logins from yesterday", "failure", "yesterday", "*", "auth", "action=failure time=yesterday source=auth"],
        ["list all successful logins in the last 7 days", "success", "last7d", "*", "auth", "action=success time=last7d source=auth"],
        ["who accessed the system from IP 10.0.0.1 today", "access", "today", "*", "host", "action=access time=today source=host"],
        ["all password change events for user jsmith this week", "login", "last7d", "jsmith", "auth", "action=login user=jsmith time=last7d source=auth"],
        ["errors in web server logs in the past hour", "error", "last1h", "*", "web", "action=error time=last1h source=web"],
        ["show me downloads by user root in last 24 hours", "download", "last24h", "root", "filesystem", "action=download user=root time=last24h source=filesystem"],
        ["requests with status code 500 since midnight", "error", "today", "*", "web", "action=error time=today source=web status=500"],
        ["find logins by anonymous users last month", "login", "last30d", "anonymous", "auth", "action=login user=anonymous time=last30d source=auth"],
        ["show web traffic from IP range 192.168.0.0/16 yesterday", "access", "yesterday", "*", "web", "action=access time=yesterday source=web"],
        ["who accessed server01 between 2pm and 4pm", "access", "today", "*", "host", "action=access time=today source=host"],
        ["list all sudo usage by any user in last week", "access", "last7d", "*", "auth", "action=access time=last7d source=auth"],
        ["when did apache restart in the last 30 minutes", "restart", "last1h", "*", "web", "action=restart time=last1h source=web"],
        ["find all failed database connections", "failure", "last24h", "*", "database", "action=failure time=last24h source=database"],
        ["who deleted files in /var/log directory", "deletion", "last7d", "*", "filesystem", "action=deletion time=last7d source=filesystem"],
        ["instances of brute force attacks last day", "failure", "last24h", "*", "auth", "action=failure time=last24h source=auth"],
        ["requests to /admin endpoint returning 403", "access", "today", "*", "web", "action=access time=today source=web status=403"],
        ["list all log entries tagged as security alert today", "error", "today", "*", "auth", "action=error time=today source=auth"],
        ["who logged out yesterday", "logout", "yesterday", "*", "auth", "action=logout time=yesterday source=auth"],
        ["count file read operations on temp directory last hour", "access", "last1h", "*", "filesystem", "action=access time=last1h source=filesystem"],
        ["show web requests by user bob last month", "access", "last30d", "bob", "web", "action=access user=bob time=last30d source=web"],
    ]
    return gold

def save_dataset(filename="log_query_dataset.csv"):
    rows = generate_queries()
    rows.extend(fixed_gold_examples())
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["nl_query", "action", "time", "user", "source", "structured_query"])
        writer.writerows(rows)
    print(f"Saved {len(rows)} examples to {filename}")

if __name__ == "__main__":
    save_dataset()
