# -*- coding: utf-8 -*-
"""
Xoa cac truong thua khoi realtime_health_data va training_health_data.

realtime_health_data: chi giu _id + 12 features
training_health_data: chi giu _id + 12 features + label
"""
import os
import sys

sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

# 12 feature fields (giu lai)
FEATURE_FIELDS = {
    "bpm", "spo2", "body_temp", "gsr_adc",
    "bpm_spo2_ratio", "temp_gsr_interaction", "bpm_temp_product", "spo2_gsr_ratio",
    "bpm_deviation", "temp_deviation", "gsr_deviation", "physiological_stress_index"
}

# Cac truong can xoa khoi realtime_health_data
REALTIME_UNSET = {
    "device_id": "", "timestamp": "", "ingested_at": "",
    "predicted_label": "", "confidence": "", "mode": "",
    "user_id": "", "time_slot": ""
}


def cleanup_realtime():
    """Strip unwanted fields from realtime_health_data; keep _id + 12 features."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    coll = db["realtime_health_data"]

    total = coll.count_documents({})
    print(f"\n{'='*60}")
    print(f"  CLEANUP: realtime_health_data")
    print(f"{'='*60}")
    print(f"  MongoDB   : {MONGO_URI}")
    print(f"  Database  : {MONGO_DB}")
    print(f"  Tong docs : {total}")

    # Kiem tra cac truong hien tai
    sample = coll.find_one()
    if sample:
        current_fields = set(sample.keys()) - {"_id"}
        print(f"  Cac truong hien tai : {sorted(current_fields)}")
    else:
        print("  Collection trong.")
        return

    # Xoa cac truong thua (ngoai _id + 12 features)
    result = coll.update_many({}, {"$unset": REALTIME_UNSET})
    print(f"\n  Da xoa cac truong: {list(REALTIME_UNSET.keys())}")
    print(f"  Documents affected : {result.modified_count}")

    # Verify
    sample2 = coll.find_one()
    if sample2:
        kept_fields = set(sample2.keys()) - {"_id"}
        print(f"\n  Cac truong con lai sau cleanup:")
        for f in sorted(kept_fields):
            print(f"    {f}: {sample2[f]}")

    client.close()


if __name__ == "__main__":
    cleanup_realtime()
