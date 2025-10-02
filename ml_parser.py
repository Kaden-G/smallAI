#!/usr/bin/env python3
"""
ML-based log query parser (starter version)
-------------------------------------------
- Uses scikit-learn with a simple TF-IDF + Logistic Regression model.
- Treats each slot (action, time, user, source) as its own classification problem.
- Compares predictions against the gold dataset (log_query_dataset.csv).
- Rule-based parser gave ~90% accuracy; this ML parser is the next step.
"""

import csv
import sys
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

DATASET_FILE = os.path.join(os.path.dirname(__file__), "datasets", "log_query_dataset.csv")

# -------------------------------
# Load dataset
# -------------------------------
import csv
from pathlib import Path

# Build dataset path relative to the repo
DATASET_PATH = Path(__file__).resolve().parent.parent / "dataset" / "log_query_dataset.csv"

def load_dataset():
    """Load the training dataset from dataset/log_query_dataset.csv"""
    with open(DATASET_FILE, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # X = natural language queries
    X = [row["nl_query"].lower() for row in rows]

    # y = labels for each slot
    y_action = [row["action"] for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source
def load_dataset(filename=None):
    if filename is None:
        filename = DATASET_FILE
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # X = natural language queries
    X = [row["nl_query"].lower() for row in rows]

    # y = labels for each slot
    y_action = [row["action"] for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source



# -------------------------------
# Train a classifier for one slot
# -------------------------------
def train_classifier(X, y, label_name="slot"):
    """
    Train a text classifier for one slot.
    Uses TF-IDF (turns text into weighted word features)
    + Logistic Regression (simple linear classifier).
    """
    # Split into train/test sets (80/20 split)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Build pipeline: vectorizer + classifier
    clf = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),  # unigrams + bigrams
        ("lr", LogisticRegression(max_iter=200))
    ])
#!/usr/bin/env python3
"""
ML-based log query parser (cleaned)
- Uses TF-IDF + Logistic Regression per-slot classifier.
"""

import csv
import sys
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# Default dataset location (absolute path inside repo)
DATASET_FILE = os.path.join(os.path.dirname(__file__), "datasets", "log_query_dataset.csv")


def load_dataset(filename=None):
    if filename is None:
        filename = DATASET_FILE
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = [row["nl_query"].lower() for row in rows]
    y_action = [row["action"] for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source


def train_classifier(X, y, label_name="slot"):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("lr", LogisticRegression(max_iter=200))
    ])
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"[{label_name}] Accuracy: {acc:.2%}")
    print(classification_report(y_test, y_pred))
    return clf


def train_all():
    X, y_action, y_time, y_user, y_source = load_dataset()
    print("Training classifiers for each slot...\n")
    clf_action = train_classifier(X, y_action, "action")
    clf_time = train_classifier(X, y_time, "time")
    clf_user = train_classifier(X, y_user, "user")
    clf_source = train_classifier(X, y_source, "source")
    return clf_action, clf_time, clf_user, clf_source


def predict_query(query, clf_action, clf_time, clf_user, clf_source):
    q = query.lower()
    return {
        "action": clf_action.predict([q])[0],
        "time": clf_time.predict([q])[0],
        "user": clf_user.predict([q])[0],
        "source": clf_source.predict([q])[0],
    }


if __name__ == "__main__":
    if len(sys.argv) == 1:
        train_all()
    else:
        models = train_all()
        nl_query = " ".join(sys.argv[1:])
        parsed = predict_query(nl_query, *models)
        print("\nNL Query:", nl_query)
        print("Predicted:", parsed)

