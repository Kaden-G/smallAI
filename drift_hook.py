"""
drift_hook.py
Purpose: Log queries that fail parsing or have low confidence,
so they can be recycled into training or rule updates later.
"""

import os
from datetime import datetime

UNPARSED_LOG = "logs/unparsed.log"


def log_unparsed(query: str, reason: str = "unknown"):
    """
    Append an unparsed or low-confidence query to logs/unparsed.log
    with timestamp and reason.
    """
    os.makedirs(os.path.dirname(UNPARSED_LOG), exist_ok=True)
    with open(UNPARSED_LOG, "a") as f:
        f.write(f"{datetime.utcnow().isoformat()}\t{reason}\t{query}\n")
