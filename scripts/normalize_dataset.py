#!/usr/bin/env python3
"""
scripts/normalize_dataset.py

Normalize dataset values using aliases in docs/schema.yaml.

Usage (dry-run, safe):
  python scripts/normalize_dataset.py dataset/log_query_dataset.csv docs/schema.yaml

To apply changes in place (creates a timestamped backup):
  python scripts/normalize_dataset.py dataset/log_query_dataset.csv docs/schema.yaml --apply

Outputs:
  - prints summary to stdout
  - writes a report to <dataset>.normalize_report.txt
  - if --apply: replaces dataset CSV and saves a backup copy

Owner: @kaden
"""
import argparse
import csv
import datetime
import sys
from pathlib import Path
import yaml
from collections import defaultdict

def load_schema(schema_path: Path):
    with open(schema_path, "r") as f:
        return yaml.safe_load(f)

def build_alias_maps(schema: dict):
    """
    Build a mapping per slot: { slot_name: {alias_lower: canonical_value, ...}, ...}
    """
    alias_maps = {}
    slots = schema.get("slots", {})
    for slot_name, slot_def in slots.items():
        aliases = slot_def.get("aliases", {}) or {}
        m = {}
        for k, v in aliases.items():
            if k is None:
                continue
            m[str(k).strip().lower()] = str(v)
        alias_maps[slot_name] = m
    return alias_maps

def normalize_cell(value):
    if value is None:
        return ""
    return str(value).strip()

def map_value(value, alias_map):
    """
    Map value using alias_map (lowercased) if present, else return original value.
    """
    if value is None:
        return value
    key = str(value).strip().lower()
    return alias_map.get(key, value)

def validate_against_schema(value, slot_def):
    """
    Check whether `value` is valid for the slot according to slot_def['values'] if enum,
    or allow anything for string_or_wildcard.
    """
    if value is None:
        return False
    t = slot_def.get("type", "")
    if t == "enum":
        allowed = [str(v) for v in slot_def.get("values", [])]
        return str(value) in allowed
    elif t == "string_or_wildcard":
        # require not-empty, wildcard allowed
        s = str(value).strip()
        return s != ""
    else:
        # unknown type: accept (conservative)
        return True

def process(csv_path: Path, schema_path: Path, apply_changes: bool = False, report_limit: int = 200):
    schema = load_schema(schema_path)
    alias_maps = build_alias_maps(schema)
    slots = schema.get("slots", {})

    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"[ERROR] dataset not found: {csv_path}")
        sys.exit(2)

    # Read CSV
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not fieldnames:
        print("[ERROR] CSV has no header / columns")
        sys.exit(3)

    # Track changes and invalids
    change_counts = defaultdict(int)
    invalid_rows = []
    sample_changes = defaultdict(list)  # slot -> [(rownum, orig, mapped), ...]

    for i, row in enumerate(rows, start=1):
        # For each slot configured in schema, attempt to map and validate
        row_changed = False
        for slot_name, slot_def in slots.items():
            # only handle columns present in CSV
            if slot_name not in row:
                continue
            orig = normalize_cell(row[slot_name])
            mapped = map_value(orig, alias_maps.get(slot_name, {}))
            # If mapped is still string but canonical may be non-lowercased; convert mapped to str
            mapped = "" if mapped is None else str(mapped).strip()
            if mapped != orig:
                change_counts[slot_name] += 1
                row[slot_name] = mapped
                row_changed = True
                if len(sample_changes[slot_name]) < 10:
                    sample_changes[slot_name].append((i, orig, mapped))
            # validate after mapping
            valid = validate_against_schema(mapped, slot_def)
            if not valid:
                invalid_rows.append((i, slot_name, orig, mapped, row["nl_query"] if "nl_query" in row else ""))

    # Summary
    now = datetime.datetime.utcnow().isoformat()
    report_path = csv_path.with_name(csv_path.name + ".normalize_report.txt")
    with open(report_path, "w", encoding="utf-8") as rep:
        rep.write(f"Normalization report for {csv_path}\n")
        rep.write(f"Schema: {schema_path}\n")
        rep.write(f"Generated: {now} UTC\n\n")
        rep.write("Change counts:\n")
        for slot, cnt in change_counts.items():
            rep.write(f"  {slot}: {cnt}\n")
        rep.write("\nSample changes (up to 10 per slot):\n")
        for slot, samples in sample_changes.items():
            rep.write(f"\n[{slot}]\n")
            for (r, o, m) in samples:
                rep.write(f"  row {r}: '{o}' -> '{m}'\n")
        rep.write("\nInvalid rows after mapping (first 200):\n")
        for idx, (rownum, slot, orig, mapped, nl) in enumerate(invalid_rows):
            if idx >= report_limit:
                break
            rep.write(f"Row {rownum}: slot={slot}, orig='{orig}', mapped='{mapped}'\n")
            rep.write(f"  NL: {nl}\n")
        rep.write(f"\nTotal invalid rows after mapping: {len(invalid_rows)}\n")

    # Print summary to stdout
    print("Normalization summary:")
    for slot, cnt in change_counts.items():
        print(f"  {slot}: {cnt} changes")
    print(f"Invalid rows after mapping: {len(invalid_rows)}")
    print(f"Report written to: {report_path}")

    if len(invalid_rows) > 0 and not apply_changes:
        print("\n[DRY-RUN] to apply changes run with --apply (creates a backup).")

    # Apply changes if requested
    if apply_changes:
        backup_path = csv_path.with_name(csv_path.name + f".backup.{now.replace(':','-')}")
        # write backup
        csv_path.rename(backup_path)
        print(f"Backup of original saved to: {backup_path}")
        # write new csv
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        print(f"Applied normalized values and wrote new dataset to: {csv_path}")

def main():
    parser = argparse.ArgumentParser(description="Normalize dataset values using schema aliases.")
    parser.add_argument("dataset_csv", help="Path to dataset CSV")
    parser.add_argument("schema_yaml", help="Path to docs/schema.yaml")
    parser.add_argument("--apply", action="store_true", help="Apply changes in-place (creates a backup).")
    parser.add_argument("--report-limit", type=int, default=200, help="How many invalid rows to include in report")
    args = parser.parse_args()

    process(Path(args.dataset_csv), Path(args.schema_yaml), apply_changes=args.apply, report_limit=args.report_limit)

if __name__ == "__main__":
    main()
