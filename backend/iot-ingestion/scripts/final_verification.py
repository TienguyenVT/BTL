# -*- coding: utf-8 -*-
"""Final verification: kiem tra ca 2 collection theo dung format yeu cau."""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from collections import Counter

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

EXPECTED_FEATURES = [
    "bpm","spo2","body_temp","gsr_adc",
    "bpm_spo2_ratio","temp_gsr_interaction","bpm_temp_product","spo2_gsr_ratio",
    "bpm_deviation","temp_deviation","gsr_deviation","physiological_stress_index"
]

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# ── 1. realtime_health_data ─────────────────────────────────
print("=" * 60)
print("  1. realtime_health_data")
print("=" * 60)
coll_rt = db["realtime_health_data"]
total_rt = coll_rt.count_documents({})
print("Tong docs: " + str(total_rt))

sample_rt = coll_rt.find_one()
if sample_rt:
    fields_rt = sorted(set(sample_rt.keys()) - {"_id"})
    print("Cac truong (ngoai _id): " + str(fields_rt))
    expected_rt = sorted(EXPECTED_FEATURES)
    if fields_rt == expected_rt:
        print("[OK] realtime_health_data: DUNG format (_id + 12 features)")
    else:
        missing = set(expected_rt) - set(fields_rt)
        extra = set(fields_rt) - set(expected_rt)
        if missing: print("[MISSING] " + str(missing))
        if extra:   print("[EXTRA] " + str(extra))
    print("\n  1 mau mau:")
    for k, v in sample_rt.items():
        print("    " + str(k) + ": " + str(v))

# ── 2. training_health_data ──────────────────────────────────
print("\n" + "=" * 60)
print("  2. training_health_data")
print("=" * 60)
coll_tr = db["training_health_data"]
total_tr = coll_tr.count_documents({})
print("Tong docs: " + str(total_tr))

sample_tr = coll_tr.find_one()
if sample_tr:
    fields_tr = sorted(set(sample_tr.keys()) - {"_id"})
    print("Cac truong (ngoai _id): " + str(fields_tr))
    expected_tr = sorted(EXPECTED_FEATURES + ["label"])
    if fields_tr == expected_tr:
        print("[OK] training_health_data: DUNG format (_id + 12 features + label)")
    else:
        missing = set(expected_tr) - set(fields_tr)
        extra = set(fields_tr) - set(expected_tr)
        if missing: print("[MISSING] " + str(missing))
        if extra:   print("[EXTRA] " + str(extra))

    label_dist = Counter(doc.get("label","") for doc in coll_tr.find({}, {"label":1}))
    print("\n  Label distribution:")
    for k, v in label_dist.items():
        print("    " + str(k) + ": " + str(v))
    print("\n  1 mau mau:")
    for k, v in sample_tr.items():
        print("    " + str(k) + ": " + str(v))

print("\n" + "=" * 60)
print("  HOAN TAT VERIFICATION")
print("=" * 60)
client.close()
