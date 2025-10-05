#!/usr/bin/env python3
"""
detect_drift.py
Purpose: Detect dataset drift between training data and new queries
using statistical tests and distribution metrics.
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cosine
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Add src to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

DRIFT_LOG = ROOT / "logs" / "drift_report.log"


def kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """
    Compute KL divergence between two probability distributions.
    KL(P||Q) = sum(p_i * log(p_i / q_i))
    """
    p = np.asarray(p) + epsilon
    q = np.asarray(q) + epsilon

    # Normalize to probabilities
    p = p / p.sum()
    q = q / q.sum()

    return np.sum(p * np.log(p / q))


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """
    Compute Jensen-Shannon divergence (symmetric version of KL).
    JS(P||Q) = 0.5 * KL(P||M) + 0.5 * KL(Q||M) where M = 0.5(P+Q)
    """
    p = np.asarray(p)
    q = np.asarray(q)
    m = 0.5 * (p + q)
    return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)


def compute_tfidf_drift(train_queries: List[str], new_queries: List[str]) -> Dict:
    """
    Compute TF-IDF vocabulary drift using cosine distance between
    mean TF-IDF vectors of training and new queries.

    Returns:
        - cosine_distance: 0 = identical, 1 = completely different
        - vocabulary_overlap: % of new query terms present in training vocab
    """
    if not train_queries or not new_queries:
        return {"cosine_distance": None, "vocabulary_overlap": None, "status": "insufficient_data"}

    vectorizer = TfidfVectorizer(max_features=1000, lowercase=True)

    # Fit on training data
    train_tfidf = vectorizer.fit_transform(train_queries)
    train_mean = train_tfidf.mean(axis=0).A1  # Convert to 1D array

    # Transform new queries
    new_tfidf = vectorizer.transform(new_queries)
    new_mean = new_tfidf.mean(axis=0).A1

    # Compute cosine distance
    cos_dist = cosine(train_mean, new_mean)

    # Vocabulary overlap
    train_vocab = set(vectorizer.vocabulary_.keys())
    new_vocab = set()
    for query in new_queries:
        new_vocab.update(query.lower().split())

    overlap = len(new_vocab & train_vocab) / len(new_vocab) if new_vocab else 0.0

    return {
        "cosine_distance": float(cos_dist),
        "vocabulary_overlap": float(overlap),
        "status": "ok"
    }


def compute_slot_distribution_drift(train_df: pd.DataFrame, new_df: pd.DataFrame,
                                    slots: List[str]) -> Dict:
    """
    Compute KL and JS divergence for each slot's value distribution.

    Returns dict of {slot: {kl_divergence, js_divergence}}
    """
    results = {}

    for slot in slots:
        if slot not in train_df.columns or slot not in new_df.columns:
            results[slot] = {"kl_divergence": None, "js_divergence": None, "status": "missing"}
            continue

        # Get value counts
        train_counts = train_df[slot].fillna("*").value_counts(normalize=False)
        new_counts = new_df[slot].fillna("*").value_counts(normalize=False)

        # Create aligned distributions
        all_values = sorted(set(train_counts.index) | set(new_counts.index))
        train_dist = np.array([train_counts.get(v, 0) for v in all_values], dtype=float)
        new_dist = np.array([new_counts.get(v, 0) for v in all_values], dtype=float)

        # Normalize
        train_dist = train_dist / train_dist.sum() if train_dist.sum() > 0 else train_dist
        new_dist = new_dist / new_dist.sum() if new_dist.sum() > 0 else new_dist

        try:
            kl = kl_divergence(new_dist, train_dist)
            js = js_divergence(train_dist, new_dist)
            results[slot] = {
                "kl_divergence": float(kl),
                "js_divergence": float(js),
                "status": "ok"
            }
        except Exception as e:
            results[slot] = {"kl_divergence": None, "js_divergence": None, "status": f"error: {e}"}

    return results


def compute_length_drift(train_queries: List[str], new_queries: List[str]) -> Dict:
    """
    Use Kolmogorov-Smirnov test to detect distribution shift in query lengths.

    Returns:
        - ks_statistic: measure of max distance between CDFs (0-1)
        - p_value: probability that distributions are the same
        - drift_detected: True if p < 0.05
    """
    train_lengths = [len(q.split()) for q in train_queries]
    new_lengths = [len(q.split()) for q in new_queries]

    if not train_lengths or not new_lengths:
        return {"ks_statistic": None, "p_value": None, "drift_detected": None, "status": "insufficient_data"}

    ks_stat, p_value = stats.ks_2samp(train_lengths, new_lengths)

    return {
        "ks_statistic": float(ks_stat),
        "p_value": float(p_value),
        "drift_detected": bool(p_value < 0.05),
        "mean_train_length": float(np.mean(train_lengths)),
        "mean_new_length": float(np.mean(new_lengths)),
        "status": "ok"
    }


def detect_drift(train_csv: str, new_csv: str, output_json: str = None) -> Dict:
    """
    Main drift detection function.

    Args:
        train_csv: Path to training dataset
        new_csv: Path to new queries dataset
        output_json: Optional path to save results

    Returns:
        Dict with all drift metrics
    """
    train_df = pd.read_csv(train_csv)
    new_df = pd.read_csv(new_csv)

    slots = ["action", "time", "user", "source", "src_ip", "hostname", "severity", "status_code"]

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "train_dataset": str(train_csv),
        "new_dataset": str(new_csv),
        "train_size": len(train_df),
        "new_size": len(new_df),
        "metrics": {}
    }

    # TF-IDF drift
    print("[INFO] Computing TF-IDF vocabulary drift...")
    results["metrics"]["tfidf"] = compute_tfidf_drift(
        train_df["nl_query"].tolist(),
        new_df["nl_query"].tolist()
    )

    # Slot distribution drift
    print("[INFO] Computing slot distribution drift...")
    results["metrics"]["slot_distributions"] = compute_slot_distribution_drift(
        train_df, new_df, slots
    )

    # Query length drift
    print("[INFO] Computing query length drift...")
    results["metrics"]["query_length"] = compute_length_drift(
        train_df["nl_query"].tolist(),
        new_df["nl_query"].tolist()
    )

    # Overall drift assessment
    tfidf_drifted = bool(results["metrics"]["tfidf"].get("cosine_distance", 0) > 0.3)
    length_drifted = bool(results["metrics"]["query_length"].get("drift_detected", False))

    slot_drift_count = sum(
        1 for slot_metrics in results["metrics"]["slot_distributions"].values()
        if slot_metrics.get("js_divergence", 0) and slot_metrics["js_divergence"] > 0.1
    )

    results["drift_summary"] = {
        "tfidf_drift_detected": bool(tfidf_drifted),
        "length_drift_detected": bool(length_drifted),
        "slots_with_drift": int(slot_drift_count),
        "overall_drift": bool(tfidf_drifted or length_drifted or slot_drift_count >= 3)
    }

    # Save to JSON
    if output_json:
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[INFO] Drift report saved to {output_json}")

    # Log to drift_report.log
    log_drift_summary(results)

    return results


def log_drift_summary(results: Dict):
    """Append drift summary to logs/drift_report.log"""
    os.makedirs(os.path.dirname(DRIFT_LOG), exist_ok=True)

    with open(DRIFT_LOG, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Drift Report - {results['timestamp']}\n")
        f.write(f"{'='*80}\n")
        f.write(f"Training dataset: {results['train_dataset']} ({results['train_size']} queries)\n")
        f.write(f"New dataset: {results['new_dataset']} ({results['new_size']} queries)\n\n")

        f.write("TF-IDF Drift:\n")
        tfidf = results["metrics"]["tfidf"]
        f.write(f"  - Cosine distance: {tfidf.get('cosine_distance', 'N/A'):.4f}\n")
        f.write(f"  - Vocabulary overlap: {tfidf.get('vocabulary_overlap', 'N/A'):.2%}\n\n")

        f.write("Query Length Drift:\n")
        length = results["metrics"]["query_length"]
        f.write(f"  - KS statistic: {length.get('ks_statistic', 'N/A'):.4f}\n")
        f.write(f"  - p-value: {length.get('p_value', 'N/A'):.4f}\n")
        f.write(f"  - Drift detected: {length.get('drift_detected', 'N/A')}\n\n")

        f.write("Slot Distribution Drift (JS Divergence):\n")
        for slot, metrics in results["metrics"]["slot_distributions"].items():
            js = metrics.get('js_divergence')
            if js is not None:
                f.write(f"  - {slot:15s}: {js:.4f}\n")

        f.write(f"\nOVERALL DRIFT: {results['drift_summary']['overall_drift']}\n")
        f.write(f"{'='*80}\n")


def main():
    """CLI for drift detection"""
    import argparse

    parser = argparse.ArgumentParser(description="Detect dataset drift")
    parser.add_argument("--train", default=str(ROOT / "datasets" / "train_queries.csv"),
                        help="Training dataset CSV")
    parser.add_argument("--new", required=True,
                        help="New queries dataset CSV")
    parser.add_argument("--output", default=str(ROOT / "reports" / "drift_report.json"),
                        help="Output JSON report path")

    args = parser.parse_args()

    results = detect_drift(args.train, args.new, args.output)

    # Print summary
    print("\n" + "="*80)
    print("DRIFT DETECTION SUMMARY")
    print("="*80)
    print(f"TF-IDF cosine distance: {results['metrics']['tfidf'].get('cosine_distance', 'N/A'):.4f}")
    print(f"Vocabulary overlap: {results['metrics']['tfidf'].get('vocabulary_overlap', 'N/A'):.2%}")
    print(f"Query length drift: {results['metrics']['query_length'].get('drift_detected', 'N/A')}")
    print(f"Slots with drift: {results['drift_summary']['slots_with_drift']}/8")
    print(f"\nOVERALL DRIFT DETECTED: {results['drift_summary']['overall_drift']}")
    print("="*80)


if __name__ == "__main__":
    main()
