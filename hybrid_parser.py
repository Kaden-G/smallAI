#!/usr/bin/env python3
#!/usr/bin/env python3

import argparse
import sys
from rule_based_parser import parse_query as rule_parse
import ml_parser
from normalizer import normalize_slots
from drift_hook import log_unparsed


CONF_THRESHOLD = 0.6


def map_time_to_bounds(time_slot: str) -> str:
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


def build_spl(parsed: dict, index: str = "smallai", nl_query: str = "") -> str:
    if not parsed:
        return f"index={index} | noop  # no parse"

    parts = [f"index={index}"]
    if parsed.get("source"):
        parts.append(f"sourcetype={parsed['source']}")
    if parsed.get("action") and parsed["action"].lower() not in ["show", "list", "display", "fetch"]:
        parts.append(f"action={parsed['action']}")
    if parsed.get("user"):
        parts.append(f"user={parsed['user']}")
    if parsed.get("time"):
        parts.append(map_time_to_bounds(parsed["time"]))

    base_query = " ".join(parts)

    group_field = None
    if nl_query:
        nl_lower = nl_query.lower()
        if "group by" in nl_lower:
            group_field = nl_lower.split("group by")[-1].strip().split()[0]
        elif "count by" in nl_lower:
            group_field = nl_lower.split("count by")[-1].strip().split()[0]

    if group_field:
        return f"{base_query} | stats count by {group_field}"

    return base_query


def parse_ml(query: str):
    # Train in-memory (small demo) and predict
    clf_action, clf_time, clf_user, clf_source = ml_parser.train_all()
    parsed = ml_parser.predict_query(query, clf_action, clf_time, clf_user, clf_source)
    # ml_parser.predict_query returns a dict (no confidence); set confidence=1.0
    return parsed, 1.0


def parse_query(query: str, force_rule: bool = False) -> dict:
    result = None
    confidence = 0.0

    if not force_rule:
        try:
            parsed_ml = parse_ml(query)
            if isinstance(parsed_ml, tuple):
                result, confidence = parsed_ml
            else:
                result = parsed_ml
                confidence = 1.0
        except Exception as e:
            print(f"[WARN] ML parser failed: {e}")
            result = None

    # Fallback to rule-based when needed
    if force_rule or not result or confidence < CONF_THRESHOLD or not any(result.values()):
        rb = rule_parse(query)
        if result:
            for k, v in rb.items():
                if not result.get(k):
                    result[k] = v
        else:
            result = rb

    # If still no usable parse → log drift
    if not result or not any(v not in [None, "*"] for v in result.values()):
        log_unparsed(query, reason="no_parse")
        return None

    # Extra drift logging: low confidence
    if confidence < 0.6:
        log_unparsed(query, reason=f"low_confidence:{confidence:.2f}")

    # Extra drift logging: spurious slots (ignore '*' which is just fallback)
    q_lower = query.lower()
    if result.get("user") not in [None, "*"] and result["user"] not in q_lower:
        log_unparsed(query, reason=f"spurious_user:{result['user']}")
    if result.get("source") not in [None, "*"] and result["source"] not in q_lower:
        log_unparsed(query, reason=f"spurious_source:{result['source']}")

    return normalize_slots(result)


def evaluate_all():
    X, y_action, y_time, y_user, y_source = ml_parser.load_dataset()
    total = len(X)
    slot_correct = {"action": 0, "time": 0, "user": 0, "source": 0}
    exact_match = 0

    for i, q in enumerate(X):
        res = parse_query(q, force_rule=False) or {}
        if res.get("action") == y_action[i]:
            slot_correct["action"] += 1
        if res.get("time") == y_time[i]:
            slot_correct["time"] += 1
        if res.get("user") == y_user[i]:
            slot_correct["user"] += 1
        if res.get("source") == y_source[i]:
            slot_correct["source"] += 1

        if (
            res.get("action") == y_action[i]
            and res.get("time") == y_time[i]
            and res.get("user") == y_user[i]
            and res.get("source") == y_source[i]
        ):
            exact_match += 1

    print(f"Evaluated {total} samples")
    for slot, correct in slot_correct.items():
        acc = correct / total * 100 if total else 0.0
        print(f"  {slot.capitalize()} accuracy: {acc:.2f}%")
    print(f"  Exact-match accuracy: {exact_match / total * 100:.2f}%")


def main():
    parser = argparse.ArgumentParser(description="Hybrid parser for NL -> SPL")
    parser.add_argument("query", type=str, nargs="?", help="Natural language query")
    parser.add_argument("-f", "--force-rule", action="store_true", help="Force rule-based parser")
    args = parser.parse_args()

    if args.query is None:
        evaluate_all()
        return

    parsed = parse_query(args.query, force_rule=args.force_rule)
    spl = build_spl(parsed, nl_query=args.query)

    print("Input:", args.query)
    print("Parsed:", parsed)
    print("SPL:", spl)
if __name__ == "__main__":
    main()
