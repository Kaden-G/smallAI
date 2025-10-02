#!/usr/bin/env python3

import argparse
import importlib

# Safe import for rule-based parser (fallback)
def safe_import_rule_parser():
    try:
        module = importlib.import_module("rule_based_parser")
        return getattr(
            module,
            "parse_rule_based",
            lambda q: {"action": None, "time": None, "user": None, "source": None},
        )
    except ImportError:
        return lambda q: {"action": None, "time": None, "user": None, "source": None}


parse_rule_based = safe_import_rule_parser()

# Import ML parser
from ml_parser import parse_ml


def map_time_to_bounds(time_slot: str) -> str:
    """Convert normalized time slot strings into Splunk earliest/latest syntax."""
    if not time_slot:
        return ""
    mapping = {
        "last1h": "earliest=-60m latest=now",
        "last24h": "earliest=-24h latest=now",
        "last30d": "earliest=-30d@d latest=now",
        "yesterday": "earliest=@d-1d latest=@d",
        "today": "earliest=@d latest=now",
        "thisweek": "earliest=@w0 latest=now",
        "lastweek": "earliest=-1w@w0 latest=@w0",
        "sinceyesterday": "earliest=@d-1d latest=now",
    }
    return mapping.get(time_slot.lower(), f"time={time_slot}")


def build_spl(parsed: dict, index: str = "smallai") -> str:
    """Build Splunk SPL query string from parsed slots."""
    parts = [f"index={index}"]

    # Add sourcetype if present
    if parsed.get("source"):
        parts.append(f"sourcetype={parsed['source']}")

    # Only add action if it’s meaningful (not “show” intent)
    if parsed.get("action") and parsed["action"].lower() not in ["show", "list", "display", "fetch"]:
        parts.append(f"action={parsed['action']}")

    # Add user if specified
    if parsed.get("user"):
        parts.append(f"user={parsed['user']}")

    # Add time bounds
    if parsed.get("time"):
        parts.append(map_time_to_bounds(parsed["time"]))

    return " ".join(parts)


def parse_query(query: str, force_rule: bool = False) -> dict:
    """
    Parse a query using ML-first, rule-based fallback approach.
    If force_rule=True, skips ML and uses rule parser only.
    """
    result = None

    if not force_rule:
        try:
            result = parse_ml(query)
        except Exception as e:
            print(f"[WARN] ML parser failed: {e}")
            result = None

    # Fallback if ML missing or incomplete
    if not result or not all(result.values()):
        rule_result = parse_rule_based(query)
        if result:
            for k, v in rule_result.items():
                if not result.get(k):
                    result[k] = v
        else:
            result = rule_result

    return result


def main():
    parser = argparse.ArgumentParser(description="Hybrid parser for NL -> SPL")
    parser.add_argument("query", type=str, nargs="?", help="Natural language query")
    parser.add_argument(
        "-f", "--force-rule", action="store_true", help="Force rule-based parser"
    )
    args = parser.parse_args()

    if args.query is None:
        # No query passed → run evaluation
        from ml_parser import load_dataset

        X, y_action, y_time, y_user, y_source = load_dataset()
        total = len(X)

        slot_correct = {"action": 0, "time": 0, "user": 0, "source": 0}
        exact_match = 0

        for i, q in enumerate(X):
            result = parse_query(q, force_rule=args.force_rule)

            # Per-slot accuracy
            if result.get("action") == y_action[i]:
                slot_correct["action"] += 1
            if result.get("time") == y_time[i]:
                slot_correct["time"] += 1
            if result.get("user") == y_user[i]:
                slot_correct["user"] += 1
            if result.get("source") == y_source[i]:
                slot_correct["source"] += 1

            # Exact-match accuracy
            if (
                result.get("action") == y_action[i]
                and result.get("time") == y_time[i]
                and result.get("user") == y_user[i]
                and result.get("source") == y_source[i]
            ):
                exact_match += 1

        print(f"Evaluated {total} samples")
        for slot, correct in slot_correct.items():
            acc = correct / total * 100 if total else 0.0
            print(f"  {slot.capitalize()} accuracy: {acc:.2f}%")

        print(f"  Exact-match accuracy: {exact_match / total * 100:.2f}%")
        return

    # Normal query mode
    parsed = parse_query(args.query, force_rule=args.force_rule)
    spl = build_spl(parsed)

    print("Input:", args.query)
    print("Parsed:", parsed)
    print("SPL:", spl)


if __name__ == "__main__":
    main()
