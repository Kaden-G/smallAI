"""
drift_hook.py
Purpose: Log queries that fail parsing or have low confidence,
and detect dataset drift for production monitoring.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd

# Add src to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))

UNPARSED_LOG = ROOT / "logs" / "unparsed.log"
UNPARSED_CSV = ROOT / "logs" / "unparsed_queries.csv"


def log_unparsed(query: str, reason: str = "unknown", slots: Optional[dict] = None):
    """
    Append an unparsed or low-confidence query to logs/unparsed.log
    with timestamp and reason.

    Also saves to unparsed_queries.csv for drift analysis.
    """
    os.makedirs(os.path.dirname(UNPARSED_LOG), exist_ok=True)

    # Log to text file
    with open(UNPARSED_LOG, "a") as f:
        f.write(f"{datetime.utcnow().isoformat()}\t{reason}\t{query}\n")

    # Log to CSV for drift detection
    log_to_csv(query, reason, slots)


def log_to_csv(query: str, reason: str, slots: Optional[dict] = None):
    """
    Append query to unparsed_queries.csv in the same format as train_queries.csv
    for drift detection analysis.
    """
    slots = slots or {}

    row = {
        "nl_query": query,
        "action": slots.get("action", "*"),
        "time": slots.get("time", "*"),
        "user": slots.get("user", "*"),
        "source": slots.get("source", "*"),
        "src_ip": slots.get("src_ip", "*"),
        "hostname": slots.get("hostname", "*"),
        "severity": slots.get("severity", "*"),
        "status_code": slots.get("status_code", "*"),
        "structured_query": "",  # Empty for unparsed
        "event_ts": datetime.utcnow().isoformat(),
        "reason": reason
    }

    df = pd.DataFrame([row])

    # Append or create CSV
    if UNPARSED_CSV.exists():
        df.to_csv(UNPARSED_CSV, mode="a", header=False, index=False)
    else:
        df.to_csv(UNPARSED_CSV, mode="w", header=True, index=False)


def check_drift_threshold(threshold: int = 100):
    """
    Check if unparsed queries have accumulated beyond threshold.
    If so, trigger drift detection analysis.

    Args:
        threshold: Number of unparsed queries to trigger drift check

    Returns:
        True if drift analysis was triggered, False otherwise
    """
    if not UNPARSED_CSV.exists():
        return False

    df = pd.read_csv(UNPARSED_CSV)

    if len(df) < threshold:
        return False

    print(f"[DRIFT] {len(df)} unparsed queries accumulated. Running drift detection...")

    # Run drift detection
    try:
        from detect_drift import detect_drift

        train_csv = ROOT / "datasets" / "train_queries.csv"
        output_json = ROOT / "reports" / "drift_report.json"

        results = detect_drift(str(train_csv), str(UNPARSED_CSV), str(output_json))

        if results["drift_summary"]["overall_drift"]:
            print("[DRIFT] ⚠️  DRIFT DETECTED! Consider retraining models.")
            print(f"[DRIFT]   - TF-IDF drift: {results['drift_summary']['tfidf_drift_detected']}")
            print(f"[DRIFT]   - Length drift: {results['drift_summary']['length_drift_detected']}")
            print(f"[DRIFT]   - Slots with drift: {results['drift_summary']['slots_with_drift']}/8")
        else:
            print("[DRIFT] ✓ No significant drift detected.")

        return True

    except Exception as e:
        print(f"[DRIFT] Error running drift detection: {e}")
        return False
