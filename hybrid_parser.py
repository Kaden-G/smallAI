#!/usr/bin/env python3
"""
Hybrid Parser for converting natural language queries into structured Splunk SPL queries.
Uses a combination of ML predictions and rule-based parsing for robust, explainable results.
"""

import re
import sys
import yaml
from pathlib import Path

# Use a wildcard index for general deployment (instead of a specific index like "smallai").
DEFAULT_INDEX = "*"

# Load schema map once
SCHEMA_PATH = Path(__file__).parent / "config" / "schema_map.yaml"
if SCHEMA_PATH.exists():
    with open(SCHEMA_PATH, "r") as f:
        SCHEMA_MAP = yaml.safe_load(f)
else:
    SCHEMA_MAP = {}

# Model persistence settings
MODELS_DIR = Path(__file__).parent / "models"
MODEL_FILES = {
    "action": MODELS_DIR / "action_classifier.joblib",
    "time": MODELS_DIR / "time_classifier.joblib",
    "user": MODELS_DIR / "user_classifier.joblib",
    "source": MODELS_DIR / "source_classifier.joblib",
    "src_ip": MODELS_DIR / "src_ip_classifier.joblib",
    "hostname": MODELS_DIR / "hostname_classifier.joblib",
    "severity": MODELS_DIR / "severity_classifier.joblib",
    "status_code": MODELS_DIR / "status_code_classifier.joblib",
}

# Global cache for loaded models
_MODELS_CACHE = None

def save_models(classifiers: dict):
    """
    Save trained ML models to disk using joblib.

    Args:
        classifiers: Dict of trained sklearn Pipeline objects (one per slot)
    """
    import joblib

    MODELS_DIR.mkdir(exist_ok=True)

    for slot_name, model_path in MODEL_FILES.items():
        joblib.dump(classifiers[slot_name], model_path)

    print(f"Models saved to {MODELS_DIR}/")

def load_models():
    """
    Load trained ML models from disk.

    Returns:
        Dict of classifiers or None if models don't exist
    """
    import joblib

    # Check if all model files exist
    if not all(f.exists() for f in MODEL_FILES.values()):
        return None

    classifiers = {}
    for slot_name, model_path in MODEL_FILES.items():
        classifiers[slot_name] = joblib.load(model_path)

    return classifiers

def train_and_save_models():
    """
    Train ML models using ml_parser and save them to disk.
    """
    import ml_parser

    print("Training ML models (8 classifiers)...")
    classifiers = ml_parser.train_all()
    print("Training complete.")

    save_models(classifiers)

def ml_predict_slots(query, models=None):
    """
    ML model prediction for query slots using saved models.

    Args:
        query: Natural language query string
        models: Optional dict of classifiers (one per slot)
                If None, attempts to load from disk

    Returns:
        Dict with predicted slots, or {} if models unavailable
    """
    global _MODELS_CACHE

    # Try to use provided models, cached models, or load from disk
    if models is None:
        if _MODELS_CACHE is None:
            _MODELS_CACHE = load_models()
        models = _MODELS_CACHE

    if models is None:
        return {}  # No models available

    import ml_parser
    return ml_parser.predict_query(query, models)

def normalize_text(query):
    return query.strip()

def field_exists(dataset_name: str, field: str) -> bool:
    """Return True if a field exists in the known schema for a dataset."""
    try:
        return field in SCHEMA_MAP.get(dataset_name, {}).get("fields", [])
    except Exception:
        return False

def parse_natural_language(query):
    """
    Hybrid parsing: Use ML predictions, fall back to rule-based for missing/low-confidence slots.
    """
    import rule_based_parser

    q = normalize_text(query)

    # Get ML predictions
    ml_slots = ml_predict_slots(q)

    # Get rule-based predictions as fallback
    rule_slots = rule_based_parser.parse_query(q)

    # Merge: Start with rule-based (high precision), override with ML when confident
    slots = {}
    for key in ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]:
        ml_val = ml_slots.get(key)
        rule_val = rule_slots.get(key)

        # Strategy: Use rule-based if it found something, otherwise use ML
        # Exception: For 'time', be more conservative - only use ML if query mentions time
        if rule_val and rule_val != "*":
            slots[key] = rule_val
        elif ml_val and ml_val != "*":
            # Special case: Don't default to ML time predictions when no time mentioned
            # Check if query actually contains time-related words
            if key == "time":
                time_keywords = ["hour", "day", "week", "month", "yesterday", "today", "since", "last", "past", "ago"]
                has_time_keyword = any(kw in q.lower() for kw in time_keywords)
                if has_time_keyword:
                    slots[key] = ml_val
                else:
                    slots[key] = "*"  # No time mentioned, don't add arbitrary time filter
            else:
                slots[key] = ml_val
        else:
            slots[key] = "*"

    return slots

def generate_spl_query(slots, query=""):
    """
    Generate Splunk SPL query from parsed slots.
    Uses sourcetype-aware field mappings for real-world compatibility.
    """
    source_type = slots.get("source", "*")

    # Start with index
    spl = f'search index={DEFAULT_INDEX}'

    # Add sourcetype based on source (more specific than source)
    sourcetype_map = {
        "web": "access_combined",  # Apache/nginx access logs
        "auth": "syslog",           # Auth logs
        "ssh": "syslog",            # SSH logs
        "database": "database",     # DB logs
        "filesystem": "syslog",     # Filesystem logs
        "host": "syslog",           # Host logs
        "firewall": "firewall",     # Firewall logs
        "windows": "WinEventLog",   # Windows Event Logs
    }

    if source_type in sourcetype_map:
        spl += f' sourcetype="{sourcetype_map[source_type]}"'
    elif source_type != "*":
        spl += f' sourcetype="{source_type}"'

    # IP address - use sourcetype-specific field names
    if slots.get("src_ip") and slots["src_ip"] not in (None, "*"):
        ip = slots["src_ip"]
        if source_type == "web":
            # Apache/nginx use 'clientip' or just search raw
            spl += f' (clientip="{ip}" OR src_ip="{ip}" OR "{ip}")'
        else:
            spl += f' (src_ip="{ip}" OR src="{ip}" OR "{ip}")'

    # Hostname filter
    if slots.get("hostname") and slots["hostname"] not in (None, "*"):
        spl += f' host="{slots["hostname"]}"'

    # User filter
    if slots.get("user") and slots["user"] not in (None, "*"):
        spl += f' (user="{slots["user"]}" OR username="{slots["user"]}")'

    # Status code (HTTP-specific)
    if slots.get("status_code") and slots["status_code"] not in (None, "*"):
        spl += f' status="{slots["status_code"]}"'

    # Action/event type - use sourcetype-specific field names
    action = slots.get("action")
    if action and action not in (None, "*"):
        if source_type == "web":
            # For web logs, search in raw text rather than action field
            action_keywords = {
                "error": '(status>=400)',
                "access": '*',  # All requests
                "success": '(status>=200 status<400)',
            }
            if action in action_keywords and action_keywords[action] != '*':
                spl += f' {action_keywords[action]}'
        elif source_type == "firewall":
            # Firewall logs use 'action' field
            spl += f' action="{action}"'
        elif source_type == "windows":
            # Windows Event Logs use EventCode
            event_code_map = {
                "failure": "4625",  # Failed login
                "success": "4624",  # Successful login
                "creation": "4720", # User created
                "deletion": "4726", # User deleted
            }
            if action in event_code_map:
                spl += f' EventCode="{event_code_map[action]}"'
            else:
                spl += f' (action="{action}" OR "{action}")'
        else:
            # For other sources, use action field or search keywords
            spl += f' (action="{action}" OR "{action}")'

    # Severity filter (only for syslog-based sources, not web logs)
    if slots.get("severity") and slots["severity"] not in (None, "*"):
        # Web logs don't have severity field - use status code ranges instead
        if source_type != "web":
            spl += f' (log_level="{slots["severity"]}" OR severity="{slots["severity"]}")'

    # Time range
    if slots.get("time") and slots["time"] not in (None, "*"):
        time_map = {
            "last1h": "-1h",
            "last24h": "-24h",
            "last7d": "-7d@d",
            "last30d": "-30d",
            "last48h": "-48h",
            "yesterday": "-1d@d",
            "today": "@d"
        }
        if slots["time"] in time_map:
            spl += f' earliest={time_map[slots["time"]]}'

    # --- Phase 3 enhancement: smarter NOC/Web context merge ---
    noc_terms = ["critical", "crit", "warn", "warning", "alert"]
    if any(term in query.lower() for term in noc_terms):
        # If generated SPL already includes HTTP status codes, merge NOC terms
        if "(status>=" in spl:
            import re
            spl = re.sub(
                r'\(status>=(\d+)\)',
                r'(status>=\1 OR status="CRIT" OR status="WARN" OR status="Critical" OR status="Warning") /* blended contexts */',
                spl,
                count=1
            )
        elif 'status="' in spl:
            # For exact status codes like status="404", append NOC terms
            spl = spl.replace(
                'status="',
                '(status="',
                1  # Only replace first occurrence
            )
            # Find position after the status code value and insert NOC terms
            import re
            spl = re.sub(
                r'status="(\d+)"',
                r'(status="\1" OR status="CRIT" OR status="WARN" OR status="Critical" OR status="Warning") /* blended contexts */',
                spl,
                count=1
            )
        else:
            # otherwise just add NOC-style conditions
            spl = 'search index=* (status="CRIT" OR status="WARN" OR status="Critical" OR status="Warning") earliest=-24h@h latest=now'

    # --- Phase 3 field-awareness filter ---
    # Remove clauses for fields that don't exist in the active dataset schema
    import re
    spl = re.sub(r'\s*\(log_level="[^"]*"\s+OR\s+severity="[^"]*"\)', '', spl)

    # --- Schema awareness cleanup ---
    active_dataset = "access_combined" if "access_combined" in spl else "noc_sample_logs"

    for field in ["log_level", "severity", "action", "status", "bytes", "clientip"]:
        if not field_exists(active_dataset, field):
            # remove unsupported clauses for this dataset
            spl = re.sub(rf'\({field}="[^"]*"\s+OR\s+"{field}"\)', '', spl)
            spl = re.sub(rf'{field}="[^"]*"', '', spl)

    # Clean up dangling OR operators and empty parentheses
    spl = re.sub(r'\(\s+OR\s+', '(', spl)
    spl = re.sub(r'\s+OR\s+\)', ')', spl)
    spl = re.sub(r'\(\s*\)', '', spl)
    spl = re.sub(r'\("[^"]*"\)\s*', '', spl)  # Remove orphaned quoted strings in parens
    spl = re.sub(r'\s+', ' ', spl).strip()

    # Balance parentheses
    open_count = spl.count('(')
    close_count = spl.count(')')
    if open_count > close_count:
        spl += ')' * (open_count - close_count)
    elif close_count > open_count:
        # Remove extra closing parens from the end
        extra = close_count - open_count
        for _ in range(extra):
            spl = spl.rstrip(') ')

    return spl

def generate_loose_spl(slots):
    """
    Generate SPL using only raw text searches (no field filters).
    Use this when field extractions don't work in your Splunk.
    """
    source_type = slots.get("source", "*")

    sourcetype_map = {
        "web": "access_combined",
        "auth": "syslog",
        "ssh": "syslog",
        "database": "database",
        "filesystem": "syslog",
        "host": "syslog",
        "firewall": "firewall",
        "windows": "WinEventLog",
    }

    spl = f'search index=*'

    # Add sourcetype
    if source_type in sourcetype_map:
        spl += f' sourcetype="{sourcetype_map[source_type]}"'
    elif source_type != "*":
        spl += f' sourcetype="{source_type}"'

    # Add time range
    if slots.get("time") and slots["time"] not in (None, "*"):
        time_map = {
            "last1h": "-1h",
            "last24h": "-24h",
            "last7d": "-7d@d",
            "last30d": "-30d",
            "last48h": "-48h",
            "yesterday": "-1d@d",
            "today": "@d"
        }
        if slots["time"] in time_map:
            spl += f' earliest={time_map[slots["time"]]}'

    # Add raw text searches for key values
    search_terms = []

    if slots.get("status_code") and slots["status_code"] != "*":
        search_terms.append(f'"{slots["status_code"]}"')

    if slots.get("src_ip") and slots["src_ip"] != "*":
        search_terms.append(f'"{slots["src_ip"]}"')

    if slots.get("user") and slots["user"] != "*":
        search_terms.append(f'"{slots["user"]}"')

    if slots.get("hostname") and slots["hostname"] != "*":
        search_terms.append(f'"{slots["hostname"]}"')

    if search_terms:
        spl += ' ' + ' '.join(search_terms)

    return spl

def main():
    if len(sys.argv) < 2:
        print("Usage: ./hybrid_parser.py [--train] [--debug] \"<natural language query>\"")
        sys.exit(1)

    # Handle --train flag
    if sys.argv[1] == "--train":
        train_and_save_models()
        return

    # Handle --debug and --loose flags
    debug_mode = False
    loose_mode = False
    query_start = 1

    if len(sys.argv) > 1 and sys.argv[1] in ["--debug", "--loose"]:
        if sys.argv[1] == "--debug":
            debug_mode = True
        elif sys.argv[1] == "--loose":
            loose_mode = True
        query_start = 2

    # Load models once at startup
    models = load_models()
    if models is None:
        print("Warning: No trained models found. Run with --train first, or models will use rule-based only.")
        print(f"Expected models in: {MODELS_DIR}/")

    query = " ".join(sys.argv[query_start:])
    slots = parse_natural_language(query)

    if loose_mode:
        spl = generate_loose_spl(slots)
    else:
        spl = generate_spl_query(slots, query)

    print("Input:", query)
    print("Parsed Slots:", slots)
    print("SPL:", spl)

    # Debug mode: generate diagnostic queries
    if debug_mode:
        print("\n=== DEBUGGING QUERIES ===")
        source_type = slots.get("source", "*")

        sourcetype_map = {
            "web": "access_combined",
            "auth": "syslog",
            "ssh": "syslog",
            "database": "database",
            "filesystem": "syslog",
            "host": "syslog",
            "firewall": "firewall",
            "windows": "WinEventLog",
        }

        expected_sourcetype = sourcetype_map.get(source_type, source_type)

        print("\n1. Check if any data exists with this sourcetype:")
        print(f'   index=* sourcetype="{expected_sourcetype}" | head 10')

        print("\n2. Find all available sourcetypes in your Splunk:")
        print('   index=* | stats count by sourcetype')

        print("\n3. Search for your criteria in raw text (if sourcetype exists):")
        if slots.get("status_code") and slots["status_code"] != "*":
            print(f'   index=* sourcetype="{expected_sourcetype}" "{slots["status_code"]}"')
        elif slots.get("src_ip") and slots["src_ip"] != "*":
            print(f'   index=* sourcetype="{expected_sourcetype}" "{slots["src_ip"]}"')
        else:
            print(f'   index=* sourcetype="{expected_sourcetype}"')

        print("\n4. Check available fields in this sourcetype:")
        print(f'   index=* sourcetype="{expected_sourcetype}" | fieldsummary | table field values')

        print("\n5. Simplified SPL (remove field filters, just search raw):")
        simple_spl = f'search index=* sourcetype="{expected_sourcetype}"'
        if slots.get("time") and slots["time"] != "*":
            time_map = {
                "last1h": "-1h",
                "last24h": "-24h",
                "last7d": "-7d@d",
                "last30d": "-30d",
                "last48h": "-48h",
                "yesterday": "-1d@d",
                "today": "@d"
            }
            if slots["time"] in time_map:
                simple_spl += f' earliest={time_map[slots["time"]]}'

        # Add raw text search for key values
        if slots.get("status_code") and slots["status_code"] != "*":
            simple_spl += f' "{slots["status_code"]}"'
        elif slots.get("src_ip") and slots["src_ip"] != "*":
            simple_spl += f' "{slots["src_ip"]}"'

        print(f'   {simple_spl}')

if __name__ == "__main__":
    main()
