# -*- coding: utf-8 -*-
"""
Truy van database - Liet ke tat ca bang (collections) va cac truong du lieu.
"""
import os
import sys

sys.path.insert(0, r"d:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"d:\Documents\BTL\backend\iot-ingestion\.env")

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

print("=" * 80)
print("  THONG TIN DATABASE")
print("=" * 80)
print(f"\n  MongoDB: {MONGO_URI}")
print(f"  Database: {MONGO_DB}")
print()

collections = db.list_collection_names()
print(f"  Tong so collections: {len(collections)}")
print()

for coll_name in sorted(collections):
    coll = db[coll_name]
    count = coll.count_documents({})

    # Lay 1 sample de xem cau truc
    sample = coll.find_one()

    # Kiem tra xem la view hay collection
    is_view = False
    try:
        coll.find_one()
    except Exception:
        is_view = True

    print("-" * 80)
    print(f"  [{coll_name}]")
    print(f"    So documents: {count}")

    if sample:
        print(f"    Cac truong (fields):")
        # Lay tat ca keys tu sample (co the co nested)
        def get_all_keys(doc, prefix=""):
            keys = []
            for k, v in doc.items():
                if isinstance(v, dict):
                    keys.extend(get_all_keys(v, prefix + k + "."))
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    keys.extend(get_all_keys(v[0], prefix + k + "[0]."))
                else:
                    type_name = type(v).__name__
                    if isinstance(v, str) and len(v) > 50:
                        val_str = v[:47] + "..."
                    else:
                        val_str = str(v)
                    keys.append((prefix + k, type_name, val_str))
            return keys

        all_keys = get_all_keys(sample)
        for field_name, field_type, sample_val in sorted(all_keys):
            print(f"      - {field_name:<40} ({field_type:<15}) = {sample_val[:30]}")

print()
print("=" * 80)
print("  XONG")
print("=" * 80)

client.close()
