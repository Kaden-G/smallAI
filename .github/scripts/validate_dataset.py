#!/usr/bin/env python3
# Validate source
source_val = row['source'].strip()
allowed_sources = [str(v) for v in schema['slots']['source']['values']]
if source_val not in allowed_sources:
errors.append(f"invalid source: '{source_val}'")


return errors




def validate_csv(csv_path, schema):
issues = []
with open(csv_path, newline='') as f:
reader = csv.DictReader(f)
rownum = 1
for row in reader:
errs = validate_row(row, schema)
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
issues = validate_csv(csv_path, schema)


if not issues:
print("Dataset validation: OK — no issues found.")
sys.exit(0)


print(f"Dataset validation: FOUND {len(issues)} problematic rows:\n")
for rownum, row, errs in issues[:50]: # show first 50
print(f"Row {rownum}: {errs}")
print(f" NL: {row.get('nl_query','')}")
print(f" action={row.get('action','')}, time={row.get('time','')}, user={row.get('user','')}, source={row.get('source','')}\n")


if len(issues) > 50:
print(f"...plus {len(issues)-50} more rows with issues")


sys.exit(1)




if __name__ == '__main__':
main()