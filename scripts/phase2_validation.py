#!/usr/bin/env python3
"""
Phase 2 validation script
- Trains/evaluates rule-based, ML, and hybrid parsers on a dataset
- Uses a train/test split for realistic evaluation
- Produces a markdown accuracy report at docs/accuracy_report.md
"""

import os
import csv
from collections import Counter
from datetime import datetime, timezone
import sys
from sklearn.model_selection import train_test_split

ROOT = os.path.dirname(os.path.dirname(__file__))
DATASET = os.path.join(ROOT, "datasets", "log_query_dataset.csv")
REPORT_MD = os.path.join(ROOT, "docs", "accuracy_report.md")

sys.path.insert(0, ROOT)
from rule_based_parser import parse_query as rule_parse, structured_string
import ml_parser
from hybrid_parser import build_spl
from drift_hook import UNPARSED_LOG

REAL_QUERIES = {
    "auth": ["show failed logins from yesterday from auth by user alice"],
    "web": ["count 500 errors in nginx logs for the last 24 hours"],
    "ssh": ["display ssh connection failures for host server-1 in the last hour"],
    "filesystem": ["list file deletion events this week on /var/log"],
    "database": ["show database errors from postgres in the last 7 days"]
}

ROBUSTNESS_QUERIES = [
    "",
    "%%%%%@@@@@",
    "show me",
    "this is a very long query " + "x " * 2000,
]

def load_dataset(path=DATASET):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)

def norm(v):
    return None if v is None else str(v).strip().lower()

def evaluate_rule_based(rows):
    total, exact = len(rows), 0
    per_field = Counter()
    fields = ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]

    for r in rows:
        parsed = rule_parse(r["nl_query"])
        pred = structured_string(parsed)
        expected = structured_string({f: r.get(f) for f in fields})

        if norm(pred) == norm(expected):
            exact += 1
        for f in fields:
            if norm(parsed.get(f)) == norm(r[f]):
                per_field[f] += 1

    return {"total": total, "exact": exact, "per_field": dict(per_field)}

def evaluate_ml(X_test, y_test, classifiers):
    fields = ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]
    preds = [ml_parser.predict_query(q, classifiers) for q in X_test]

    total, exact = len(X_test), 0
    per_field = Counter()
    for i, p in enumerate(preds):
        for f in fields:
            if norm(p.get(f)) == norm(y_test[f][i]):
                per_field[f] += 1
        if all(norm(p.get(f)) == norm(y_test[f][i]) for f in fields):
            exact += 1

    return {"total": total, "exact": exact, "per_field": dict(per_field)}

def evaluate_hybrid(X_test, y_test, classifiers):
    fields = ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]
    total, exact = len(X_test), 0
    per_field = Counter()

    for i, q in enumerate(X_test):
        ml_pred = ml_parser.predict_query(q, classifiers)
        rb = rule_parse(q)

        combined = {}
        for slot in fields:
            v = ml_pred.get(slot)
            if v in [None, "*"]:
                v = rb.get(slot)
            combined[slot] = v

        if all(norm(combined.get(f)) == norm(y_test[f][i]) for f in fields):
            exact += 1

        for f in fields:
            if norm(combined.get(f)) == norm(y_test[f][i]):
                per_field[f] += 1

    return {"total": total, "exact": exact, "per_field": dict(per_field)}

def write_report(rule_stats, ml_stats, hybrid_stats, real_checks, robustness_checks):
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def pct(count, total):
        return round((count / total) * 100) if total else 0

    header = (
        f"# Phase 2 Validation Report\nGenerated: {ts}\n\n"
        "## Overview\n"
        "This report summarizes the performance of the SmallAI Hybrid Parser after completing Phase 2 (Execution/MVP).\n\n"
    )

    with open(REPORT_MD, "w") as f:
        f.write(header)
        f.write("## Key Results\n")
        for name, stats in [("Action", "action"), ("Time", "time"), ("User", "user"), ("Source", "source")]:
            f.write(f"- **{name} slot:** {pct(ml_stats['per_field'].get(stats, 0), ml_stats['total'])}% accuracy\n")
        f.write("\n")

        f.write("## Summary\n")
        f.write(f"- Dataset rows evaluated (test set): {ml_stats['total']}\n")
        f.write(f"- Rule exact-match: {rule_stats['exact']} / {rule_stats['total']} ({rule_stats['exact']/rule_stats['total']:.2%})\n")
        f.write(f"- ML exact-match: {ml_stats['exact']} / {ml_stats['total']} ({ml_stats['exact']/ml_stats['total']:.2%})\n")
        f.write(f"- Hybrid exact-match: {hybrid_stats['exact']} / {hybrid_stats['total']} ({hybrid_stats['exact']/hybrid_stats['total']:.2%})\n\n")

        f.write("## Drift log (last 50 lines)\n")
        if os.path.exists(UNPARSED_LOG):
            with open(UNPARSED_LOG) as lf:
                lines = lf.readlines()[-50:]
            for L in lines:
                f.write(f"- {L}")
        else:
            f.write("- (no drift log found)\n")

    return REPORT_MD

def main():
    print("Running Phase 2 validation with train/test split...\n")
    rows = load_dataset()

    # Train/test split
    fields = ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]
    X = [r["nl_query"] for r in rows]
    y_dict = {f: [r[f] for r in rows] for f in fields}

    # Split data
    from sklearn.model_selection import train_test_split
    indices = list(range(len(X)))
    train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)

    X_train = [X[i] for i in train_idx]
    X_test = [X[i] for i in test_idx]
    y_train = {f: [y_dict[f][i] for i in train_idx] for f in fields}
    y_test = {f: [y_dict[f][i] for i in test_idx] for f in fields}

    # Train ML classifiers
    classifiers = {}
    for field in fields:
        print(f"Training {field} classifier...")
        classifiers[field] = ml_parser.train_classifier(X_train, y_train[field])

    # Evaluate all methods on the same test set
    test_rows = [{**{"nl_query": X_test[i]}, **{f: y_test[f][i] for f in fields}} for i in range(len(X_test))]

    rule_stats = evaluate_rule_based(test_rows)
    ml_stats = evaluate_ml(X_test, y_test, classifiers)
    hybrid_stats = evaluate_hybrid(X_test, y_test, classifiers)

    # Report
    report = write_report(rule_stats, ml_stats, hybrid_stats, None, None)
    print(f"Report generated: {report}")

if __name__ == "__main__":
    main()
