#!/usr/bin/env python3
"""
reset_logs.py
Utility script to clear drift logs (logs/unparsed.log).
Run this when you want a clean slate before testing/evaluating.
"""

import os

LOG_FILE = "logs/unparsed.log"

def reset_log():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    open(LOG_FILE, "w").close()
    print(f"[INFO] Cleared {LOG_FILE}")

if __name__ == "__main__":
    reset_log()

