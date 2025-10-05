#!/usr/bin/env python3
import os
import re
import csv
import sys

# Always resolve dataset relative to this script's folder
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATASET_FILE = os.path.join(BASE_DIR, "datasets", "train_queries.csv")

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
    "firewall": ["firewall", "firewall logs", "network security", "fw"],
    "windows": ["windows", "windows event", "event log", "event viewer"],
}

users = ["root", "alice", "bob", "jsmith", "admin", "anonymous"]

# NEW: IP address patterns
ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

# NEW: Hostname keywords
hostname_keywords = ["web-server", "db-prod", "firewall", "app-server", "load-balancer", "server"]

# NEW: Severity keywords
severity_keywords = {
    "critical": ["critical", "crit", "emergency"],
    "error": ["error", "err"],
    "warning": ["warning", "warn", "caution"],
    "info": ["info", "informational", "notice"],
}

# NEW: Status code patterns
status_code_pattern = r'\b(200|201|204|301|302|304|400|401|403|404|500|502|503|504)\b'

def parse_query(nl_query: str):
    text = nl_query.lower()
    parsed = {
        "action": "*",
        "time": "*",
        "user": "*",
        "source": "*",
        "src_ip": "*",
        "hostname": "*",
        "severity": "*",
        "status_code": "*"
    }

    # Action extraction (check specific patterns first)
    if re.search(r"failed login|login failure|auth failure|event 4625", text):
        parsed["action"] = "failure"
    elif re.search(r"successful login|auth success|event 4624", text):
        parsed["action"] = "success"
    elif re.search(r"\bdeny|denies|denied|block|blocks|blocked|drop|dropped|reject", text):
        parsed["action"] = "deny"
    elif re.search(r"\ballow|allows|allowed|permit|permits|permitted|accept|accepts|accepted", text):
        parsed["action"] = "allow"
    elif re.search(r"user creation|created user|event 4720", text):
        parsed["action"] = "creation"
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

    # NEW: IP extraction
    ip_match = re.search(r'(?:from|ip|address)\s+' + ip_pattern, text)
    if ip_match:
        ip_addr = re.search(ip_pattern, ip_match.group())
        if ip_addr:
            parsed["src_ip"] = ip_addr.group()
    else:
        # Try to find any IP in the text
        ip_match = re.search(ip_pattern, text)
        if ip_match:
            parsed["src_ip"] = ip_match.group()

    # NEW: Hostname extraction
    hostname_match = re.search(r'(?:on|host|server)\s+([\w-]+)', text)
    if hostname_match:
        parsed["hostname"] = hostname_match.group(1)

    # NEW: Severity extraction
    for sev, keywords in severity_keywords.items():
        if any(kw in text for kw in keywords):
            parsed["severity"] = sev
            break

    # NEW: Status code extraction
    status_match = re.search(r'(?:status|code|http)\s*' + status_code_pattern, text)
    if status_match:
        code = re.search(status_code_pattern, status_match.group())
        if code:
            parsed["status_code"] = code.group()
    else:
        # Try to find standalone status codes
        status_match = re.search(status_code_pattern, text)
        if status_match:
            parsed["status_code"] = status_match.group()

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
    if parsed.get("src_ip") and parsed["src_ip"] != "*":
        parts.append(f"src_ip={parsed['src_ip']}")
    if parsed.get("hostname") and parsed["hostname"] != "*":
        parts.append(f"hostname={parsed['hostname']}")
    if parsed.get("severity") and parsed["severity"] != "*":
        parts.append(f"severity={parsed['severity']}")
    if parsed.get("status_code") and parsed["status_code"] != "*":
        parts.append(f"status_code={parsed['status_code']}")
    return " ".join(parts)

def evaluate(dataset=DATASET_FILE, show_fails=10):
    with open(dataset, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    exact = 0
    field_correct = {"action": 0, "time": 0, "user": 0, "source": 0, "src_ip": 0, "hostname": 0, "severity": 0, "status_code": 0}
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
