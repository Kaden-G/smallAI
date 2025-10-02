import os
import csv
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

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
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = [normalize_query(row["nl_query"]) for row in rows]
    y_action = [normalize_action(row["action"]) for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source


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
    }


if __name__ == "__main__":
    # Quick test
    test_q = "Show me all the failed login attempts in the past 24hrs"
    print(parse_ml(test_q))
