#!/usr/bin/env python3
"""
Evaluate SmallAI's hybrid_parser on a batch of NL → SPL pairs.

Reads:
    datasets/eval_queries.csv
Outputs:
    reports/eval_results.csv

Purpose:
    - Runs each natural-language query through hybrid_parser.parse_query()
    - Compares generated SPL with expected SPL
    - Marks pass/fail and writes a summary report
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# import your parser (adjust path if necessary)
from src.hybrid_parser import parse_query

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
EVAL_PATH = Path("datasets/eval_queries.csv")
REPORT_PATH = Path("reports/eval_results.csv")

REPORT_PATH.parent.mkdir(exist_ok=True)

# -------------------------------------------------------------------
# Run evaluation
# -------------------------------------------------------------------
print(f"Running evaluation on {EVAL_PATH} ...")

df = pd.read_csv(EVAL_PATH)
results = []

for _, row in df.iterrows():
    nl_query = row["input"]
    expected = row["expected_spl"].strip()

    try:
        output = parse_query(nl_query)
        generated = output.get("spl", str(output)).strip()
    except Exception as e:
        generated = f"ERROR: {e}"

    passed = generated == expected
    results.append({
        "input": nl_query,
        "expected_spl": expected,
        "generated_spl": generated,
        "pass": passed
    })

out = pd.DataFrame(results)
accuracy = (out["pass"].sum() / len(out)) * 100
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -------------------------------------------------------------------
# Save results
# -------------------------------------------------------------------
out.to_csv(REPORT_PATH, index=False)
print(f"[{timestamp}] Evaluation complete: {accuracy:.1f}% accurate "
      f"({out['pass'].sum()}/{len(out)} passed)")
print(f"Results saved to {REPORT_PATH}")

# Optional: pretty summary
print("\nFailed examples:")
print(out[out["pass"] == False][["input", "generated_spl"]].to_string(index=False))
