#!/usr/bin/env python3

import argparse
import importlib

# Try to import parse_rule_based if it exists, else use a stub
def safe_import_rule_parser():
    try:
        module = importlib.import_module("rule_based_parser")
        return getattr(module, "parse_rule_based", lambda q: {"action": None, "time": None, "user": None, "source": None})
    except ImportError:
        return lambda q: {"action": None, "time": None, "user": None, "source": None}

parse_rule_based = safe_import_rule_parser()

# Import ML parser normally
from ml_parser import parse_ml


def map_time_to_bounds(time_slot: str) -> str:
    """Convert normalized time slot strings into Splunk earliest/latest syntax."""
    if not time_slot:
        return ""
    mapping = {
        "last1h": 'earliest=-60m latest=now',
        "last24h": 'earliest=-24h latest=now',
        "last30d": 'earliest=-30d@d latest=now',
        "yesterday": 'earliest=@d-1d latest=@d',
        "today": 'earliest=@d latest=now',
        "thisweek": 'earliest=@w0 latest=now',
        "lastweek": 'earliest=-1w@w0 latest=@w0',
        "sinceyesterday": 'earliest=@d-1d latest=now',
    }
    return mapping.get(time_slot.lower(), f'time={time_slot}')


def build_spl(parsed: dict, index: str = "smallai") -> str:
    """Build Splunk SPL query string from parsed slots."""
    parts = [f"index={index}"]
    if parsed.get("source"):
        parts.append(f"sourcetype={parsed['source']}")
    if parsed.get("action"):
        parts.append(f"action={parsed['action']}")
    if parsed.get("user"):
        parts.append(f"user={parsed['user']}")
    if parsed.get("time"):
        parts.append(map_time_to_bounds(parsed['time']))
    return " ".join(parts)


def parse_query(query: str, force_rule: bool = False) -> dict:
    """Parse a query using ML-first, rule-based fallback approach."""
    result = None
    if not force_rule:
        result = parse_ml(query)
    if not result or not all(result.values()):
        # fallback
        rule_result = parse_rule_based(query)
        # merge results: prefer ML if present, else rule-based
        if result:
            for k, v in rule_result.items():
                if not result.get(k):
                    result[k] = v
        else:
            result = rule_result
    return result


def main():
    parser = argparse.ArgumentParser(description="Hybrid parser for NL -> SPL")
    parser.add_argument("query", type=str, help="Natural language query")
    parser.add_argument("-f", "--force-rule", action="store_true", help="Force rule-based parser")
    args = parser.parse_args()

    parsed = parse_query(args.query, force_rule=args.force_rule)
    spl = build_spl(parsed)

    print("Input:", args.query)
    print("Parsed:", parsed)
    print("SPL:", spl)


if __name__ == "__main__":
    main()
