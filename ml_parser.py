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

import csv
<<<<<<< HEAD
import re
=======
import sys
import os
>>>>>>> feature/update-copilot-instructions
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

<<<<<<< HEAD
# Always resolve dataset relative to this script’s folder
BASE_DIR = os.path.dirname(__file__)
DATASET_FILE = os.path.join(BASE_DIR, "datasets", "log_query_dataset.csv")


def normalize_query(q: str) -> str:
    """Normalize common time phrases into canonical labels using regex."""
    q = q.lower()

    patterns = {
        # 24h variants
        r"(past|last)\s*24\s*(hours|hrs?)": "last24h",
        r"(in|within|over)\s*(the\s*)?(past\s*)?day": "last24h",
        r"since yesterday": "last24h",

        # Single-day
        r"\byesterday\b": "yesterday",
        r"\blast night\b": "yesterday",
        r"(the day before today)": "yesterday",
        r"\btoday\b": "today",
        r"(since this morning|earlier today|today so far|since midnight|this morning|this afternoon|this evening|tonight|since start of day|end of day)": "today",

        # Multi-day
        r"(yesterday and today|past two days|past couple days|past few days|past several days|recent days|couple of days)": "lastweek",

        # Week-related
        r"\bthis week\b": "thisweek",
        r"(since the start of this week|since monday|since tuesday|since wednesday|since thursday|since friday|since saturday|since sunday)": "thisweek",
        r"(last week|in the last week|past week)": "lastweek",
        r"(this weekend)": "thisweek",
        r"(last weekend|the weekend|over the weekend)": "lastweek",

        # Month-related
        r"(last 30 days|past 30 days|past month|in the last month|over the last month)": "last30d",
        r"(this month|so far this month|since the start of the month|month to date)": "last30d",
        r"(last month|previous month|end of last month)": "last30d",

        # Loose phrasing
        r"(recently)": "last24h",
        r"(lately|not long ago|the other day|previously)": "lastweek",
    }

    for pattern, norm in patterns.items():
        q = re.sub(pattern, norm, q)

    return q


def normalize_action(a: str) -> str:
    """Normalize action labels to reduce synonym mismatches."""
    mapping = {
        "list": "show",
        "display": "show",
        "error": "failure",
        "failed": "failure",
        "login_success": "success",
        "ok": "success",
    }
    return mapping.get(a.lower(), a.lower())


def load_dataset(filename=DATASET_FILE):
    """Load dataset and split into X (queries) and slot labels (action, time, user, source)."""
=======
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
>>>>>>> feature/update-copilot-instructions
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = [normalize_query(row["nl_query"]) for row in rows]
    y_action = [normalize_action(row["action"]) for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source


<<<<<<< HEAD
def train_models():
    """Train simple TF-IDF + Logistic Regression classifiers for each slot."""
    X, y_action, y_time, y_user, y_source = load_dataset()

    # Train/test split (kept simple — demo mode)
    X_train, _, y_action_train, _ = train_test_split(X, y_action, test_size=0.2, random_state=42)
    _, _, y_time_train, _ = train_test_split(X, y_time, test_size=0.2, random_state=42)
    _, _, y_user_train, _ = train_test_split(X, y_user, test_size=0.2, random_state=42)
    _, _, y_source_train, _ = train_test_split(X, y_source, test_size=0.2, random_state=42)

    # Build per-slot classifiers
    action_clf = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(max_iter=200))])
    time_clf = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(max_iter=200))])
    user_clf = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(max_iter=200))])
    source_clf = Pipeline([("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(max_iter=200))])

    # Fit classifiers
    action_clf.fit(X_train, y_action_train)
    time_clf.fit(X_train, y_time_train)
    user_clf.fit(X_train, y_user_train)
    source_clf.fit(X_train, y_source_train)

    return {
        "action": action_clf,
        "time": time_clf,
        "user": user_clf,
        "source": source_clf,
    }


# Train models once on import
MODELS = train_models()


def parse_ml(query: str) -> dict:
    """
    Parse a natural-language log query using trained ML models.
    Returns dict with slots: action, time, user, source.
    """
    query = normalize_query(query)
    return {
        "action": normalize_action(MODELS["action"].predict([query])[0]),
        "time": MODELS["time"].predict([query])[0],
        "user": MODELS["user"].predict([query])[0],
        "source": MODELS["source"].predict([query])[0],
=======

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
>>>>>>> feature/update-copilot-instructions
    }


if __name__ == "__main__":
<<<<<<< HEAD
    # Quick test
    test_q = "Show me all the failed login attempts in the past 24hrs"
    print(parse_ml(test_q))
=======
    if len(sys.argv) == 1:
        train_all()
    else:
        models = train_all()
        nl_query = " ".join(sys.argv[1:])
        parsed = predict_query(nl_query, *models)
        print("\nNL Query:", nl_query)
        print("Predicted:", parsed)

>>>>>>> feature/update-copilot-instructions
