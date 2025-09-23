#!/usr/bin/env python3
"""
scripts/validate_dataset.py
Validate dataset/log_query_dataset.csv against docs/schema.yaml with alias normalization.
Exits 0 on success; non-zero if issues found.
"""
import csv
import sys
import yaml
from pathlib import Path

def load_schema(schema_path):
    with open(schema_path, "r") as f:
        return yaml.safe_load(f)

def build_alias_map(schema):
    """Return a dict mapping lowercased alias -> canonical value"""
    alias_map = {}
    src_slot = schema.get("slots", {}).get("source", {})
    aliases = src_slot.get("aliases", {}) or {}
    # normalize keys to lowercase for robust matching
    for k, v in aliases.items():
        alias_map[str(k).lower()] = str(v)
    return alias_map

def normalize_value(val):
    return "" if val is None else str(val).strip()

def map_alias(value, alias_map):
    if not value:
        return value
    v = value.strip().lower()
    return alias_map.get(v, value)  # return canonical if found, else original

def validate_row(row, schema, alias_map):
    errors = []
    # required columns
    required_cols = ["nl_query", "action", "time", "user", "source"]
    for c in required_cols:
        if c not in row:
            errors.append(f"missing column: {c}")
            return errors

    # Validate action
    action_val = normalize_value(row["action"])
    allowed_actions = [str(v) for v in schema["slots"]["action"]["values"]]
    if action_val not in allowed_actions:
        errors.append(f"invalid action: '{action_val}'")

    # Validate time
    time_val = normalize_value(row["time"])
    allowed_times = [str(v) for v in schema["slots"]["time"]["values"]]
    if time_val not in allowed_times:
        errors.append(f"invalid time: '{time_val}'")

    # Validate user (allow wildcard '*')
    user_val = normalize_value(row["user"])
    if user_val == "":
        errors.append("empty user field")

    # Validate source — map aliases first
    source_val_raw = normalize_value(row["source"])
    source_mapped = map_alias(source_val_raw, alias_map)
    allowed_sources = [str(v) for v in schema["slots"]["source"]["values"]]
    if source_mapped not in allowed_sources:
        errors.append(f"invalid source: '{source_val_raw}' (mapped to '{source_mapped}')")

    return errors

def validate_csv(csv_path, schema, alias_map):
    issues = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rownum = 1
        for row in reader:
            errs = validate_row(row, schema, alias_map)
            if errs:
                issues.append((rownum, row, errs))
            rownum += 1
    return issues

def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/validate_dataset.py <dataset.csv> <schema.yaml>")
        sys.exit(2)

    csv_path = Path(sys.argv[1])
    schema_path = Path(sys.argv[2])

    if not csv_path.exists():
        print(f"Dataset not found: {csv_path}")
        sys.exit(3)
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}")
        sys.exit(3)

    schema = load_schema(schema_path)
    alias_map = build_alias_map(schema)
    issues = validate_csv(csv_path, schema, alias_map)

    if not issues:
        print("Dataset validation: OK — no issues found.")
        sys.exit(0)

    print(f"Dataset validation: FOUND {len(issues)} problematic rows:\n")
    for rownum, row, errs in issues[:200]:  # show first 200
        print(f"Row {rownum}: {errs}")
        print(f"  NL: {row.get('nl_query','')}")
        print(
            f"  action={row.get('action','')}, time={row.get('time','')}, user={row.get('user','')}, source={row.get('source','')}\n"
        )

    if len(issues) > 200:
        print(f"...plus {len(issues)-200} more rows with issues")

    sys.exit(1)

if __name__ == "__main__":
    main()
