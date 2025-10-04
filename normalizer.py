"""
normalizer.py
Purpose: Normalize raw slot values from ML/rule parsers into canonical schema values.
"""

def normalize_action(raw: str) -> str:
    if not raw:
        return None
    raw = raw.lower()

    # Canonical actions
    if raw in ["show", "display", "view"]:
        return "show"
    if raw in ["list", "enumerate"]:
        return "list"
    if raw in ["find", "search", "lookup"]:
        return "find"

    # Synonyms / misclassifications
    if raw in ["failure", "failures", "error", "errors", "success", "successes"]:
        return "show"   # treat as "show results"

    return raw  # fallback


def normalize_time(raw: str) -> str:
    if not raw:
        return None
    raw = raw.lower()

    mappings = {
        "last 24 hours": "last24h",
        "last24h": "last24h",
        "yesterday": "yesterday",
        "today": "today",
        "last 7 days": "last7d",
        "last week": "last7d",
        "this week": "thisweek",
        "last 30 days": "last30d",
        "last month": "last30d",
    }
    return mappings.get(raw, raw)


def normalize_user(raw: str) -> str:
    if not raw or raw.strip() in ["*", "any", "all", "unknown"]:
        return None
    return raw.strip().lower()


def normalize_source(raw: str) -> str:
    if not raw:
        return None
    raw = raw.lower()

    mappings = {
        "auth": "auth",
        "authentication": "auth",
        "login": "auth",
        "web": "web",
        "nginx": "web",
        "apache": "web",
        "ssh": "ssh",
        "system": "system",
        "sys": "system",
        "db": "db",
        "database": "db",
        "postgres": "db",
        "mysql": "db",
        "filesystem": "filesystem",
        "disk": "filesystem",
    }
    return mappings.get(raw, raw)


def normalize_src_ip(raw: str) -> str:
    """Normalize IP address (basic validation)."""
    if not raw or raw.strip() in ["*", "any", "all"]:
        return None
    # Basic IP validation - could be enhanced
    import re
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', raw.strip()):
        return raw.strip()
    return None


def normalize_hostname(raw: str) -> str:
    """Normalize hostname."""
    if not raw or raw.strip() in ["*", "any", "all", "unknown"]:
        return None
    return raw.strip().lower()


def normalize_severity(raw: str) -> str:
    """Normalize severity level."""
    if not raw or raw.strip() in ["*", "any"]:
        return None
    raw = raw.lower().strip()

    mappings = {
        "critical": "critical",
        "crit": "critical",
        "emergency": "critical",
        "error": "error",
        "err": "error",
        "warning": "warning",
        "warn": "warning",
        "caution": "warning",
        "info": "info",
        "informational": "info",
        "notice": "info",
    }
    return mappings.get(raw, raw)


def normalize_status_code(raw: str) -> str:
    """Normalize HTTP status code."""
    if not raw or raw.strip() in ["*", "any"]:
        return None
    # Return as-is if it's a valid status code
    if raw.strip().isdigit():
        return raw.strip()
    return None


def normalize_slots(slots: dict) -> dict:
    """Apply normalization to all slots in a parsed result dict."""
    return {
        "action": normalize_action(slots.get("action")),
        "time": normalize_time(slots.get("time")),
        "user": normalize_user(slots.get("user")),
        "source": normalize_source(slots.get("source")),
        "src_ip": normalize_src_ip(slots.get("src_ip")),
        "hostname": normalize_hostname(slots.get("hostname")),
        "severity": normalize_severity(slots.get("severity")),
        "status_code": normalize_status_code(slots.get("status_code")),
    }
