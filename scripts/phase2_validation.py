#!/usr/bin/env python3
"""
Phase 2 validation script
- Trains/evaluates rule-based, ML, and hybrid parsers on the synthetic dataset
- Runs a set of real-world example queries across major log types
- Produces a markdown accuracy report at docs/accuracy_report.md

Definition-of-Done checks implemented (see repo README/issue):
- rule-based baseline accuracy
- ML per-slot accuracy
- hybrid exact-match accuracy
- robustness checks for malformed input
- drift logging exercised

Usage: python3 scripts/phase2_validation.py
"""
import os
import csv
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(__file__))
DATASET = os.path.join(ROOT, "datasets", "log_query_dataset.csv")
REPORT_MD = os.path.join(ROOT, "docs", "accuracy_report.md")

# Import project modules
import sys
sys.path.insert(0, ROOT)
from rule_based_parser import parse_query as rule_parse, structured_string
import ml_parser
from hybrid_parser import build_spl
from normalizer import normalize_slots
from drift_hook import UNPARSED_LOG

# Ensure ml_parser uses the dataset path under datasets/ (ml_parser default is repo-root CSV)
ml_parser.DATASET_FILE = DATASET

# Real-world sample queries by log type (one example each)
REAL_QUERIES = {
    "auth": ["show failed logins from yesterday from auth by user alice"],
    "web": ["count 500 errors in nginx logs for the last 24 hours"],
    "ssh": ["display ssh connection failures for host server-1 in the last hour"],
    "filesystem": ["list file deletion events this week on /var/log"],
    "database": ["show database errors from postgres in the last 7 days"]
}

# Robustness/test queries (malformed / edge cases)
ROBUSTNESS_QUERIES = [
    "",  # empty
    "%%%%%@@@@@",  # symbols only
    "show me",  # too short
    "this is a very long query " + "x " * 2000,  # very long
]


def load_dataset(path=DATASET):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def evaluate_rule_based(rows):
    total = len(rows)
    exact = 0
    per_field = Counter()

    for r in rows:
        parsed = rule_parse(r["nl_query"])
        pred = structured_string(parsed)
        if pred == r["structured_query"]:
            exact += 1
        for f in ["action", "time", "user", "source"]:
            if parsed[f] == r[f]:
                per_field[f] += 1

    return {
        "total": total,
        "exact": exact,
        "per_field": dict(per_field)
    }


def evaluate_ml(rows, clfs=None):
    # Use the provided rows (loaded by the caller) rather than ml_parser.load_dataset
    X = [r["nl_query"] for r in rows]
    y_action = [r["action"] for r in rows]
    y_time = [r["time"] for r in rows]
    y_user = [r["user"] for r in rows]
    y_source = [r["source"] for r in rows]

    # If classifiers were pre-trained by the caller, use them. Otherwise train here.
    if clfs is None:
        print("Training ML classifiers (this will print per-slot evals)...")
        clf_action = ml_parser.train_classifier(X, y_action, "action")
        clf_time = ml_parser.train_classifier(X, y_time, "time")
        clf_user = ml_parser.train_classifier(X, y_user, "user")
        clf_source = ml_parser.train_classifier(X, y_source, "source")
    else:
        clf_action, clf_time, clf_user, clf_source = clfs

    preds = [ml_parser.predict_query(q, clf_action, clf_time, clf_user, clf_source) for q in X]

    total = len(X)
    per_field = Counter()
    exact = 0
    for i, p in enumerate(preds):
        if p["action"] == y_action[i]:
            per_field["action"] += 1
        if p["time"] == y_time[i]:
            per_field["time"] += 1
        if p["user"] == y_user[i]:
            per_field["user"] += 1
        if p["source"] == y_source[i]:
            per_field["source"] += 1
        if (p["action"] == y_action[i] and p["time"] == y_time[i] and p["user"] == y_user[i] and p["source"] == y_source[i]):
            exact += 1

    return {"total": total, "exact": exact, "per_field": dict(per_field)}


def evaluate_hybrid(rows, clfs=None):
    total = len(rows)
    exact = 0
    per_field = Counter()
    # Use provided classifiers if available; otherwise train once here.
    if clfs is None:
        clf_action, clf_time, clf_user, clf_source = ml_parser.train_all()
    else:
        clf_action, clf_time, clf_user, clf_source = clfs

    for r in rows:
        q = r["nl_query"]
        # ML prediction (fast; models already trained)
        ml_pred = ml_parser.predict_query(q, clf_action, clf_time, clf_user, clf_source)

        # Rule-based fallback to fill empty/placeholder slots
        rb = rule_parse(q)

        # Combine: prefer ML predictions, fill any missing/placeholder with rule-based
        combined = {}
        for slot in ["action", "time", "user", "source"]:
            v = ml_pred.get(slot)
            if v in [None, "*"]:
                v = rb.get(slot)
            combined[slot] = v

        pn = {k: (v if v not in [None, "*"] else "*") for k, v in combined.items()}
        if (pn.get("action") == r["action"] and pn.get("time") == r["time"] and pn.get("user") == r["user"] and pn.get("source") == r["source"]):
            exact += 1
        for f in ["action", "time", "user", "source"]:
            if pn.get(f) == r[f]:
                per_field[f] += 1

    return {"total": total, "exact": exact, "per_field": dict(per_field)}


def run_real_world_checks(clfs):
    results = {}
    for t, qs in REAL_QUERIES.items():
        results[t] = []
        for q in qs:
            # Use ML prediction with provided classifiers, fallback to rule-based
            ml_pred = ml_parser.predict_query(q, *clfs)
            rb = rule_parse(q)
            combined = {}
            for slot in ["action", "time", "user", "source"]:
                v = ml_pred.get(slot)
                if v in [None, "*"]:
                    v = rb.get(slot)
                combined[slot] = v
            parsed = {k: (v if v not in [None, "*"] else None) for k, v in combined.items()}
            spl = build_spl(parsed or {}, nl_query=q)
            results[t].append({"query": q, "parsed": parsed, "spl": spl})
    return results


def run_robustness_checks(clfs):
    results = []
    for q in ROBUSTNESS_QUERIES:
        try:
            ml_pred = ml_parser.predict_query(q, *clfs)
            rb = rule_parse(q)
            combined = {}
            for slot in ["action", "time", "user", "source"]:
                v = ml_pred.get(slot)
                if v in [None, "*"]:
                    v = rb.get(slot)
                combined[slot] = v
            parsed = {k: (v if v not in [None, "*"] else None) for k, v in combined.items()}
            results.append({"query": q, "parsed": parsed})
        except Exception as e:
            results.append({"query": q, "error": str(e)})
    return results


def write_report(rule_stats, ml_stats, hybrid_stats, real_checks, robustness_checks):
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, "w") as f:
        f.write(f"# Phase 2 Validation Report\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n")

        f.write("## Summary\n")
        f.write(f"- Dataset rows evaluated: {rule_stats['total']}\n")
        f.write(f"- Rule exact-match: {rule_stats['exact']} / {rule_stats['total']} ({rule_stats['exact']/rule_stats['total']:.2%})\n")
        f.write(f"- ML exact-match: {ml_stats['exact']} / {ml_stats['total']} ({ml_stats['exact']/ml_stats['total']:.2%})\n")
        f.write(f"- Hybrid exact-match: {hybrid_stats['exact']} / {hybrid_stats['total']} ({hybrid_stats['exact']/hybrid_stats['total']:.2%})\n\n")

        f.write("## Per-slot accuracy\n\n")
        f.write("### Rule-based\n")
        for k, v in rule_stats['per_field'].items():
            f.write(f"- {k}: {v} / {rule_stats['total']} ({v/rule_stats['total']:.2%})\n")
        f.write("\n### ML\n")
        for k, v in ml_stats['per_field'].items():
            f.write(f"- {k}: {v} / {ml_stats['total']} ({v/ml_stats['total']:.2%})\n")
        f.write("\n### Hybrid\n")
        for k, v in hybrid_stats['per_field'].items():
            f.write(f"- {k}: {v} / {hybrid_stats['total']} ({v/hybrid_stats['total']:.2%})\n")

        f.write("\n## Real-world sample checks\n")
        for t, items in real_checks.items():
            f.write(f"\n### {t}\n")
            for it in items:
                f.write(f"- Query: {it['query']}\n")
                f.write(f"  - Parsed: {it['parsed']}\n")
                f.write(f"  - SPL: {it['spl']}\n")

        f.write("\n## Robustness checks\n")
        for r in robustness_checks:
            f.write(f"- Query: {repr(r['query'])}\n")
            if 'error' in r:
                f.write(f"  - Error: {r['error']}\n")
            else:
                f.write(f"  - Parsed: {r['parsed']}\n")

        f.write("\n## Drift log (last 50 lines)\n")
        if os.path.exists(UNPARSED_LOG):
            with open(UNPARSED_LOG) as lf:
                lines = lf.readlines()[-50:]
            for L in lines:
                f.write(f"- {L}")
        else:
            f.write("- (no drift log found)\n")

    return REPORT_MD


def main():
    print("Running Phase 2 validation...\n")
    rows = load_dataset()
    rule_stats = evaluate_rule_based(rows)
    # Train ML models once and reuse to avoid repeated training prints
    clfs = ml_parser.train_all()
    ml_stats = evaluate_ml(rows, clfs=clfs)
    hybrid_stats = evaluate_hybrid(rows, clfs=clfs)
    real_checks = run_real_world_checks(clfs)
    robustness_checks = run_robustness_checks(clfs)
    report = write_report(rule_stats, ml_stats, hybrid_stats, real_checks, robustness_checks)
    print(f"Report generated: {report}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"Dataset not found: {e}. Place dataset at {DATASET} or run datasets/generate_dataset.py")
 