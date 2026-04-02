# -*- coding: utf-8 -*-
"""
Tao bang final_result tu datalake_raw.
Gom: timestamp, device_id, bpm, spo2, body_temp, gsr_adc, label, confidence, ingested_at.
Chi lay docs da co prediction.label (ket qua cuoi cung cua he thong).
"""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

FINAL_COLL = "final_result"

print("=" * 60)
print("  TAO BANG final_result")
print("=" * 60)

# Xoa bang cu neu ton tai
if FINAL_COLL in db.list_collection_names():
    old_count = db[FINAL_COLL].count_documents({})
    db[FINAL_COLL].drop()
    print(f"[1] Da xoa bang cu: {old_count} docs")
else:
    print("[1] Bang cu khong ton tai, bo qua.")

# Lay docs tu datalake_raw co prediction.label
source = db["datalake_raw"]
docs_with_pred = source.find({"prediction.label": {"$exists": True, "$ne": None}})

records = []
for doc in docs_with_pred:
    sensor = doc.get("sensor", {})
    pred   = doc.get("prediction", {})

    record = {
        "timestamp":    doc.get("timestamp", ""),
        "device_id":   doc.get("device_id", ""),
        "bpm":         sensor.get("bpm", None),
        "spo2":        sensor.get("spo2", None),
        "body_temp":   sensor.get("body_temp", None),
        "gsr_adc":     sensor.get("gsr_adc", None),
        "label":       pred.get("label", None),
        "confidence":  pred.get("confidence", None),
        "data_quality": doc.get("data_quality", ""),
        "source":      doc.get("source", ""),
        "ingested_at": doc.get("ingested_at", None),
        "schema_version": "1.0",
        "created_at":  datetime.now(timezone.utc),
    }
    records.append(record)

# Insert
if records:
    db[FINAL_COLL].insert_many(records)
    print(f"[2] Da insert {len(records)} docs vao '{FINAL_COLL}'")
else:
    print("[2] Khong co docs nao co prediction.label.")

# Tao indexes
db[FINAL_COLL].create_index([("timestamp", -1)])
db[FINAL_COLL].create_index([("device_id", 1), ("timestamp", -1)])
db[FINAL_COLL].create_index([("label", 1)])
db[FINAL_COLL].create_index([("ingested_at", -1)])
print("[3] Da tao 4 indexes: timestamp, device_timestamp, label, ingested_at")

# Thong ke
total = db[FINAL_COLL].count_documents({})
print(f"\n[4] Tong docs: {total}")

print("\n[5] Thong ke theo label:")
for lbl, cnt in db[FINAL_COLL].aggregate([
    {"$group": {"_id": "$label", "count": {"$sum": 1}}}
]):
    print(f"    {str(lbl)}: {cnt}")

print("\n[6] Thong ke theo device_id:")
for dev, cnt in db[FINAL_COLL].aggregate([
    {"$group": {"_id": "$device_id", "count": {"$sum": 1}}}
]):
    print(f"    {str(dev)}: {cnt}")

print("\n[7] Thong ke confidence:")
pipeline = [
    {"$match": {"confidence": {"$ne": None}}},
    {"$group": {
        "_id": None,
        "min": {"$min": "$confidence"},
        "max": {"$max": "$confidence"},
        "avg": {"$avg": "$confidence"},
        "count": {"$sum": 1}
    }}
]
for r in db[FINAL_COLL].aggregate(pipeline):
    print(f"    Min: {r['min']:.4f}")
    print(f"    Max: {r['max']:.4f}")
    print(f"    Avg: {r['avg']:.4f}")
    print(f"    Count: {r['count']}")

# Mau
print("\n[8] Mau document (khong co _id):")
sample = db[FINAL_COLL].find_one()
if sample:
    for k, v in sample.items():
        if k == "_id":
            continue
        print(f"    {str(k)}: {str(v)}")

# All collections summary
print("\n" + "=" * 60)
print("  HE THONG SAU KHI TAO final_result")
print("=" * 60)
for coll_name in db.list_collection_names():
    c = db[coll_name]
    total = c.count_documents({})
    s = c.find_one() or {}
    fields = sorted([k for k in s.keys() if k != "_id"])
    print(f"\n  [{coll_name}] ({total} docs)")
    print(f"    Fields: {fields}")

client.close()
print("\n" + "=" * 60)
print("  HOAN TAT!")
print("=" * 60)
