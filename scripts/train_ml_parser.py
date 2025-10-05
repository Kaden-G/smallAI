#!/usr/bin/env python3
"""
Train slot-specific classifiers for SmallAI's ML parser.

Each slot (action, time, user, source, src_ip, hostname, severity, status_code)
gets its own LogisticRegression classifier using a shared TF-IDF vectorizer.
"""

import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from collections import defaultdict

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
DATA_PATH = Path("datasets/train_queries.csv")
MODEL_DIR = Path("models")
REPORT_DIR = Path("reports")
MODEL_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------------------
# Slots configuration
# -------------------------------------------------------------------
SLOTS = [
    "action",
    "time",
    "user",
    "source",
    "src_ip",
    "hostname",
    "severity",
    "status_code",
]

# -------------------------------------------------------------------
# Load dataset
# -------------------------------------------------------------------
print(f"Loading dataset: {DATA_PATH}")
df = pd.read_csv(DATA_PATH)

# Expect columns: nl_query and slot names (action, time, user, etc.)
missing = [s for s in SLOTS if s not in df.columns]
if missing:
    raise ValueError(f"Missing columns for slots: {missing}")

X = df["nl_query"]

# -------------------------------------------------------------------
# Build shared vectorizer
# -------------------------------------------------------------------
print("Building shared TF-IDF vectorizer ...")
vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
X_vec = vectorizer.fit_transform(X)
joblib.dump(vectorizer, MODEL_DIR / "vectorizer.pkl")

# -------------------------------------------------------------------
# Train one classifier per slot
# -------------------------------------------------------------------
slot_scores = defaultdict(float)

for slot in SLOTS:
    y = df[slot].fillna("*")
    X_train, X_val, y_train, y_val = train_test_split(
        X_vec, y, test_size=0.2, random_state=42, shuffle=True
    )

    clf = LogisticRegression(max_iter=200)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_val)
    acc = accuracy_score(y_val, preds)
    slot_scores[slot] = acc

    joblib.dump(clf, MODEL_DIR / f"model_{slot}.pkl")
    print(f"Trained {slot:12s} → accuracy: {acc:.2f}")

# -------------------------------------------------------------------
# Write summary report
# -------------------------------------------------------------------
report_lines = ["Slot,Accuracy"]
for slot, acc in slot_scores.items():
    report_lines.append(f"{slot},{acc:.2f}")
REPORT_PATH = REPORT_DIR / "ml_slot_holdout_report.csv"
REPORT_PATH.write_text("\n".join(report_lines))

print(f"\n✅ Training complete. Results saved to {REPORT_PATH}")
