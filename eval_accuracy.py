#!/usr/bin/env python3
"""
eval_accuracy.py
Evaluate rule, ML, and hybrid parsers on both synthetic and real-world datasets.
"""

import csv
from pathlib import Path
from typing import Dict, List

# Import your existing parsers
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from rule_based_parser import parse_rule_based
from ml_parser import parse_ml
from hybrid_parser import parse_query as parse_hybrid
# Paths
SYNTHETIC_DATASET = Path("dataset/log_query_dataset.csv")
REAL_DATASET = Path("tests/real_queries.csv")

SLOTS = ["action", "time", "user", "source"]


def load_dataset(path: Path) -> List[Dict]:
    """Load a CSV dataset into memory."""
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def evaluate_parser(rows: List[Dict], parser_fn) -> Dict:
    """Evaluate a single parser function on a dataset."""
    total = len(rows)
    slot_correct = {slot: 0 for slot in SLOTS}
    exact_correct = 0
    failures = []

    for row in rows:
        # Handle datasets with either 'input' or 'query' as the NL column
        query = row.get("input") or row.get("query")
        expected = {slot: row.get(slot) or None for slot in SLOTS}

        result = parser_fn(query) or {}

        # Compare slot by slot
        slot_match = True
        for slot in SLOTS:
            if (result.get(slot) or None) == expected[slot]:
                slot_correct[slot] += 1
            else:
                slot_match = False

        if slot_match:
            exact_correct += 1
        else:
            failures.append((query, expected, result))

    # Compute accuracy
    slot_acc = {slot: round(slot_correct[slot] / total * 100, 2) for slot in SLOTS}
    exact_acc = round(exact_correct / total * 100, 2)

    return {"slot_acc": slot_acc, "exact_acc": exact_acc, "failures": failures}


def run_eval():
    datasets = {}
    if SYNTHETIC_DATASET.exists():
        datasets["Synthetic"] = load_dataset(SYNTHETIC_DATASET)
    if REAL_DATASET.exists():
        datasets["Real"] = load_dataset(REAL_DATASET)

    parsers = {
        "Rule-Based": parse_rule_based,
        "ML": parse_ml,
        "Hybrid": parse_hybrid,
    }

    for name, rows in datasets.items():
        print(f"\n=== {name} Dataset ({len(rows)} samples) ===")
        for parser_name, parser_fn in parsers.items():
            results = evaluate_parser(rows, parser_fn)
            print(f"\n[{parser_name}]")
            print("Slot Accuracy:", results["slot_acc"])
            print("Exact Match Accuracy:", results["exact_acc"], "%")
            print("Failures (up to 3):")
            for q, exp, res in results["failures"][:3]:
                print(f"  Q: {q}")
                print(f"  Expected: {exp}")
                print(f"  Got:      {res}")


if __name__ == "__main__":
    run_eval()
