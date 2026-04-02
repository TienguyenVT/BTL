# -*- coding: utf-8 -*-
"""Kiem tra training_health_data hien tai co truong nao."""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
coll = db["training_health_data"]

total = coll.count_documents({})
print(f"Tong docs: {total}")

# Xem 5 mau dau tien
print("\n--- 5 mau dau tien (tat ca truong) ---")
for doc in coll.find().limit(5):
    print(dict(doc))

# Thong ke label
if "label" in coll.find_one() or "intended_label" in coll.find_one() or "predicted_label" in coll.find_one():
    from collections import Counter
    label_field = "label" if "label" in coll.find_one() else ("intended_label" if "intended_label" in coll.find_one() else "predicted_label")
    labels = [doc.get(label_field,"") for doc in coll.find({}, {label_field: 1})]
    dist = Counter(labels)
    print(f"\n--- Label distribution ({label_field}) ---")
    for k, v in dist.items():
        print(f"  {k}: {v}")
else:
    print("\nKhong co truong label/intended_label/predicted_label")

# Xem cau truc 1 mau
sample = coll.find_one()
if sample:
    print(f"\n--- Tat ca truong cua 1 mau ---")
    for k in sample.keys():
        print(f"  {k}")

client.close()
