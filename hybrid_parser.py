#!/usr/bin/env python3
"""
Hybrid Log Query Parser with Splunk SPL Generator
-------------------------------------------------
- ML-first with rule fallback.
- Normalizes time fields.
- Generates realistic Splunk SPL queries.
- Prompts the user if key fields (source, user) are missing.
- Supports `-f` (force mode) to skip prompts and keep wildcards.
"""

<<<<<<< Updated upstream
import csv
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np
import rule_based_parser as rb

DATASET_FILE = "datasets/log_query_dataset.csv"
CONF_THRESHOLD = 0.7

# -------------------------------
# Load dataset
# -------------------------------
def load_dataset(filename=DATASET_FILE):
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = [row["nl_query"].lower() for row in rows]
    y_action = [row["action"] for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source


# -------------------------------
# Train classifiers
# -------------------------------
def train_classifier(X, y):
    clf = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("lr", LogisticRegression(max_iter=200))
    ])
    clf.fit(X, y)
    return clf
=======
import argparse
import importlib
from rule_based_parser import parse_rule_based
from ml_parser import parse_ml
from normalizer import normalize_slots
from drift_hook import log_unparsed
>>>>>>> Stashed changes


def train_all():
    X, y_action, y_time, y_user, y_source = load_dataset()
        return f"{base_query} | stats count by {group_field}"
    #!/usr/bin/env python3

    import argparse
    import importlib
    from rule_based_parser import parse_rule_based
    from ml_parser import parse_ml
    from normalizer import normalize_slots
    from drift_hook import log_unparsed


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


    def build_spl(parsed: dict, index: str = "smallai", nl_query: str = "") -> str:
        """Build Splunk SPL query string from parsed slots + optional NL query context."""
        if not parsed:
            return f"index={index} | noop  # no parse"

        parts = [f"index={index}"]

        if parsed.get("source"):
            parts.append(f"sourcetype={parsed['source']}")

        # Only include action if it’s not just a display intent
        if parsed.get("action") and parsed["action"].lower() not in ["show", "list", "display", "fetch"]:
            parts.append(f"action={parsed['action']}")

        if parsed.get("user"):
            parts.append(f"user={parsed['user']}")

        if parsed.get("time"):
            parts.append(map_time_to_bounds(parsed["time"]))

        base_query = " ".join(parts)

        # --- NEW: handle "group by" / "count by" ---
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



    def parse_query(query: str, force_rule: bool = False) -> dict:
        """
        Hybrid query parser:
        - ML first, fallback to rules if low confidence or missing slots.
        - force_rule=True → skip ML and use rules only.
        - Always normalize before returning.
        - Logs failed/low-confidence queries for drift monitoring.
        """
        result = None
        confidence = 0.0

        if not force_rule:
            try:
                parsed = parse_ml(query)
                if isinstance(parsed, tuple):
                    result, confidence = parsed
                else:
                    result = parsed
                    confidence = 1.0
            except Exception as e:
                print(f"[WARN] ML parser failed: {e}")
                result = None

        # Fallback if ML failed, low confidence, or incomplete
        if force_rule or not result or confidence < 0.6 or not any(result.values()):
            rule_result = parse_rule_based(query)
            if result:
                for k, v in rule_result.items():
                    if not result.get(k):
                        result[k] = v
            else:
                result = rule_result

        # If still no usable parse → log drift
        if not result or not any(result.values()):
            log_unparsed(query, reason="no_parse")
            return None

        # Extra drift logging: low confidence
        if confidence < 0.6:
            log_unparsed(query, reason=f"low_confidence:{confidence:.2f}")

        # Extra drift logging: spurious slots
        q_lower = query.lower()
        if result.get("user") and result["user"] not in q_lower:
            log_unparsed(query, reason=f"spurious_user:{result['user']}")
        if result.get("source") and result["source"] not in q_lower:
            log_unparsed(query, reason=f"spurious_source:{result['source']}")

        # Normalize before returning
        return normalize_slots(result)


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
                result = parse_query(q, force_rule=args.force_rule) or {}
                if result.get("action") == y_action[i]:
                    slot_correct["action"] += 1
                if result.get("time") == y_time[i]:
                    slot_correct["time"] += 1
                if result.get("user") == y_user[i]:
                    slot_correct["user"] += 1
                if result.get("source") == y_source[i]:
                    slot_correct["source"] += 1

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

        # Query mode
        parsed = parse_query(args.query, force_rule=args.force_rule)
        spl = build_spl(parsed, nl_query=args.query)

        print("Input:", args.query)
        print("Parsed:", parsed)
        print("SPL:", spl)


    if __name__ == "__main__":
        main()
    }

    # Determine sourcetype
    src = parsed.get("source", "*")
    if src in known_sourcetypes:
        st = src
    else:
        st = source_to_sourcetype.get(src, "*")

    # Build SPL parts
    parts = []
    parts.append("index=main")  # your uploads went to main
    if st != "*":
        parts.append(f"sourcetype={st}")

    action_clause = action_templates.get(parsed.get("action", "*"), "")
    if action_clause:
        parts.append(action_clause)

    user = parsed.get("user", "*")
    if user and user != "*":
        parts.append(f'user={user}')

    time_clause = time_map.get(parsed.get("time", "*"), "")
    if time_clause:
        parts.append(time_clause)

    return " ".join(parts).strip()


# -------------------------------
# Hybrid prediction
# -------------------------------
def predict_query(query, models, threshold=CONF_THRESHOLD):
    query = query.lower()
    result = {}
    rb_parsed = rb.parse_query(query)

    for slot, clf in models.items():
        proba = clf.predict_proba([query])[0]
        pred_idx = np.argmax(proba)
        pred_label = clf.classes_[pred_idx]
        confidence = proba[pred_idx]

        if confidence >= threshold:
            result[slot] = pred_label
        else:
            result[slot] = rb_parsed[slot]

    result = normalize_slots(result)
    return result
=======
    # If still no usable parse → log drift
    if not result or not any(result.values()):
        log_unparsed(query, reason="no_parse")
        return None

    # Extra drift logging: low confidence
    if confidence < 0.6:
        log_unparsed(query, reason=f"low_confidence:{confidence:.2f}")

    # Extra drift logging: spurious slots
    q_lower = query.lower()
    if result.get("user") and result["user"] not in q_lower:
        log_unparsed(query, reason=f"spurious_user:{result['user']}")
    if result.get("source") and result["source"] not in q_lower:
        log_unparsed(query, reason=f"spurious_source:{result['source']}")

    # Normalize before returning
    return normalize_slots(result)
>>>>>>> Stashed changes

from sklearn.metrics import accuracy_score

<<<<<<< Updated upstream
def evaluate_all():
    X, y_action, y_time, y_user, y_source = load_dataset()
    models = train_all()
    y_pred_action = models["action"].predict(X)
    y_pred_time = models["time"].predict(X)
    y_pred_user = models["user"].predict(X)
    y_pred_source = models["source"].predict(X)
=======
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
            result = parse_query(q, force_rule=args.force_rule) or {}
            if result.get("action") == y_action[i]:
                slot_correct["action"] += 1
            if result.get("time") == y_time[i]:
                slot_correct["time"] += 1
            if result.get("user") == y_user[i]:
                slot_correct["user"] += 1
            if result.get("source") == y_source[i]:
                slot_correct["source"] += 1

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

    # Query mode
    parsed = parse_query(args.query, force_rule=args.force_rule)
    spl = build_spl(parsed, nl_query=args.query)

    print("Input:", args.query)
    print("Parsed:", parsed)
    print("SPL:", spl)
>>>>>>> Stashed changes

    print("\n=== Evaluation Results ===")
    print(f"Action accuracy:     {accuracy_score(y_action, y_pred_action) * 100:.2f}%")
    print(f"Time accuracy:       {accuracy_score(y_time, y_pred_time) * 100:.2f}%")
    print(f"User accuracy:       {accuracy_score(y_user, y_pred_user) * 100:.2f}%")
    print(f"Sourcetype accuracy: {accuracy_score(y_source, y_pred_source) * 100:.2f}%")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    force_mode = False
    args = sys.argv[1:]

    if "-f" in args:
        force_mode = True
        args.remove("-f")

    if force_mode:
        print("⚡ Running in force mode: skipping clarification prompts.\n")

    if len(args) > 0:
        # parse a single natural-language query
        models = train_all()
        nl_query = " ".join(args)
        parsed = predict_query(nl_query, models)
        if not force_mode:
            parsed = clarification_prompt(parsed)
        spl = to_spl(parsed)
        print("\nNL Query:", nl_query)
        print("Hybrid Parsed:", parsed)
        print("Generated SPL:", spl)
    else:
        # no args → run evaluation on the dataset
        evaluate_all()
