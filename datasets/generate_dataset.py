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
    "firewall": ["firewall", "firewall logs", "network security"],
    "windows": ["windows", "windows event log", "event viewer"],
}

# NEW: IP addresses for NOC queries
src_ips = ["*", "10.0.0.1", "192.168.1.100", "172.16.0.50", "10.10.10.5", "192.168.0.1"]

# NEW: Hostnames for NOC queries
hostnames = ["*", "web-server-01", "db-prod-02", "firewall-01", "app-server-03", "load-balancer"]

# NEW: Severity levels
severities = {
    "critical": ["critical", "crit", "emergency"],
    "error": ["error", "err"],
    "warning": ["warning", "warn"],
    "info": ["info", "informational"],
    "*": ["any severity", "all levels"],
}

# NEW: HTTP status codes
status_codes = ["*", "200", "404", "500", "403", "502", "503"]

# NEW: Destination IPs for firewall logs
dest_ips = ["*", "10.0.0.10", "192.168.1.200", "172.16.0.100", "10.10.10.50"]

# NEW: Ports for firewall/network logs
ports = ["*", "22", "80", "443", "3306", "5432", "8080", "3389"]

# NEW: Protocols for firewall logs
protocols = ["*", "TCP", "UDP", "ICMP"]

# NEW: Firewall actions
firewall_actions = {
    "allow": ["allow", "permit", "accept"],
    "deny": ["deny", "block", "drop"],
    "reject": ["reject"],
}

# NEW: Windows event codes (common security events)
event_codes = ["*", "4624", "4625", "4672", "4688", "4720", "4728"]

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

def generate_structured(action_key, time_key, user, source_key, src_ip, hostname, severity, status_code):
    parts = []
    parts.append(f"action={action_key}")
    if user != "*":
        parts.append(f"user={user}")
    if source_key != "*":
        parts.append(f"source={source_key}")
    if src_ip != "*":
        parts.append(f"src_ip={src_ip}")
    if hostname != "*":
        parts.append(f"hostname={hostname}")
    if severity != "*":
        parts.append(f"severity={severity}")
    if status_code != "*":
        parts.append(f"status_code={status_code}")
    if time_key != "*":
        parts.append(map_time_to_bounds(time_key))
    return " ".join(parts)

def generate_queries(n=600):  # Increased from 480 to get more diverse examples
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

        # NEW slots (randomly include or exclude with wildcards)
        src_ip = random.choice(src_ips) if random.random() > 0.7 else "*"
        hostname = random.choice(hostnames) if random.random() > 0.7 else "*"
        severity_key = random.choice(list(severities.keys())) if random.random() > 0.7 else "*"
        severity_phrase = random.choice(severities[severity_key]) if severity_key != "*" else ""
        status_code = random.choice(status_codes) if random.random() > 0.7 else "*"

        # Construct natural language query with new fields
        user_part = "" if user == "*" else f" by user {user}"
        ip_part = "" if src_ip == "*" else f" from ip {src_ip}"
        hostname_part = "" if hostname == "*" else f" on {hostname}"
        severity_part = "" if severity_key == "*" else f" {severity_phrase}"
        status_part = "" if status_code == "*" else f" with status {status_code}"

        nl_query = f"{prefix}{severity_part} {action_phrase} events{user_part}{ip_part}{hostname_part}{status_part} {time_phrase} in {source_phrase}"

        structured = generate_structured(action_key, time_key, user, source_key, src_ip, hostname, severity_key, status_code)
        event_ts = generate_event_ts(time_key)

        rows.append([nl_query, action_key, time_key, user, source_key, src_ip, hostname, severity_key, status_code, structured, event_ts])
    return rows

def fixed_gold_examples():
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    gold = [
        # Auth/Web examples
        ["show me failed logins from yesterday", "failure", "yesterday", "*", "auth", "*", "*", "*", "*", "action=failure source=auth earliest=@d-1d latest=@d", ts],
        ["list all successful logins in the last 7 days", "success", "last7d", "*", "auth", "*", "*", "*", "*", "action=success source=auth earliest=-7d@d latest=now", ts],
        ["find all requests from ip 10.0.0.1", "access", "last24h", "*", "web", "10.0.0.1", "*", "*", "*", "action=access source=web src_ip=10.0.0.1 earliest=-24h latest=now", ts],
        ["show critical errors on web-server-01 last hour", "error", "last1h", "*", "web", "*", "web-server-01", "critical", "*", "action=error source=web hostname=web-server-01 severity=critical earliest=-60m latest=now", ts],
        ["display all 404 errors from yesterday", "error", "yesterday", "*", "web", "*", "*", "*", "404", "action=error source=web status_code=404 earliest=@d-1d latest=@d", ts],
        ["list 500 errors on app-server-03 today", "error", "today", "*", "web", "*", "app-server-03", "*", "500", "action=error source=web hostname=app-server-03 status_code=500 earliest=@d latest=now", ts],

        # Firewall examples
        ["show firewall denies from 192.168.1.100 last hour", "deny", "last1h", "*", "firewall", "192.168.1.100", "*", "*", "*", "action=deny source=firewall src_ip=192.168.1.100 earliest=-60m latest=now", ts],
        ["find blocked traffic to port 22 today", "deny", "today", "*", "firewall", "*", "*", "*", "*", "action=deny source=firewall earliest=@d latest=now", ts],
        ["list all firewall accepts from 10.0.0.1 yesterday", "allow", "yesterday", "*", "firewall", "10.0.0.1", "*", "*", "*", "action=allow source=firewall src_ip=10.0.0.1 earliest=@d-1d latest=@d", ts],

        # Windows event examples
        ["show failed login attempts on windows last 24 hours", "failure", "last24h", "*", "windows", "*", "*", "*", "*", "action=failure source=windows earliest=-24h latest=now", ts],
        ["find event 4625 from yesterday", "failure", "yesterday", "*", "windows", "*", "*", "*", "*", "action=failure source=windows earliest=@d-1d latest=@d", ts],
        ["list all user creation events this week", "creation", "last7d", "*", "windows", "*", "*", "*", "*", "action=creation source=windows earliest=-7d@d latest=now", ts],
    ]
    return gold

def save_dataset(filename="log_query_dataset.csv"):
    rows = generate_queries()
    rows.extend(fixed_gold_examples())
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["nl_query", "action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code", "structured_query", "event_ts"])
        writer.writerows(rows)
    print(f"Saved {len(rows)} examples to {filename}")

if __name__ == "__main__":
    save_dataset()