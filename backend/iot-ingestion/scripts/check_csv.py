# -*- coding: utf-8 -*-
import csv, os
csv_path = r"c:\Documents\BTL\Data\labeled_data_for_annotation.csv"
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
print(f"Total rows: {len(rows)}")
print("Columns:", reader.fieldnames)
print("First 2 rows:")
for i, r in enumerate(rows[:2]):
    print(f"  {r}")
from collections import Counter
labels = Counter(r.get("manual_label","") for r in rows)
print("manual_label distribution:", dict(labels))
