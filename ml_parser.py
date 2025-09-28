import os
import csv
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# Always resolve dataset relative to this script’s folder
BASE_DIR = os.path.dirname(__file__)
DATASET_FILE = os.path.join(BASE_DIR, "log_query_dataset.csv")

def load_dataset(filename=DATASET_FILE):
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    X = [row["nl_query"].lower() for row in rows]
    y_action = [row["action"] for row in rows]
    y_time = [row["time"] for row in rows]
    y_user = [row["user"] for row in rows]
    y_source = [row["source"] for row in rows]

    return X, y_action, y_time, y_user, y_source
