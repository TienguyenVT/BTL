# -*- coding: utf-8 -*-
"""
Chuyen final_result thanh MongoDB VIEW (thay vi hard-copy collection).
View se tu dong reflect tat ca thay doi trong datalake_raw.
"""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

FINAL_COLL = "final_result"

print("=" * 60)
print("  CHUYEN final_result -> VIEW")
print("=" * 60)

# Xoa collection cu (view khong the drop, chi drop neu la collection)
if FINAL_COLL in db.list_collection_names():
    # Kiem tra la view hay collection
    try:
        db[FINAL_COLL].drop()
        print("[1] Da xoa collection cu.")
    except Exception as e:
        print("[1] Khong the drop (co the la view): " + str(e))
else:
    print("[1] Khong co collection cu, tiep tuc.")

# Tao view bang aggregation pipeline
pipeline = [
    # Chi lay docs co prediction.label (da duoc gan nhan)
    {"$match": {
        "prediction.label": {"$exists": True, "$ne": None}
    }},
    # Flatten: tach sensor va prediction ra nhuang field bac nhat
    {"$addFields": {
        "bpm":        "$sensor.bpm",
        "spo2":      "$sensor.spo2",
        "body_temp": "$sensor.body_temp",
        "gsr_adc":   "$sensor.gsr_adc",
        "label":     "$prediction.label",
        "confidence":"$prediction.confidence",
    }},
    # Chi giu lai cac fields can thiet
    {"$project": {
        "_id": 0,
        "timestamp":   1,
        "device_id":   1,
        "bpm":         1,
        "spo2":        1,
        "body_temp":   1,
        "gsr_adc":     1,
        "label":       1,
        "confidence":  1,
        "data_quality": 1,
        "source":       1,
        "ingested_at":  1,
        "schema_version": 1,
    }},
    # Sort theo ingested_at giam dan (moi nhat truoc)
    {"$sort": {"ingested_at": -1}},
]

db.create_collection(FINAL_COLL, viewOn="datalake_raw", pipeline=pipeline)
print("[2] Da tao VIEW '" + FINAL_COLL + "' tren datalake_raw.")
print("    View se tu dong cap nhat khi datalake_raw thay doi.")

# Indexes tren view (MongoDB se apply tren underlying collection)
try:
    db[FINAL_COLL].create_index([("timestamp", -1)])
    db[FINAL_COLL].create_index([("label", 1)])
    db[FINAL_COLL].create_index([("device_id", 1), ("timestamp", -1)])
    print("[3] Da tao 3 indexes tren view.")
except Exception as e:
    print("[3] Indexes: " + str(e))

# Verify
print()
print("=" * 60)
print("  XAC MINH VIEW")
print("=" * 60)

# Check view
coll_info = db.command({"listCollections": 1, "filter": {"name": FINAL_COLL}})
for c in coll_info.get("cursor", {}).get("firstBatch", []):
    print("  Type: " + c.get("type", "collection"))
    opts = c.get("options", {})
    print("  View on: " + opts.get("viewOn", "N/A"))
    print("  Fields (schema): " + str(list(opts.get("pipeline", [{}]))))

total = db[FINAL_COLL].count_documents({})
print()
print("  Tong docs trong view: " + str(total))

print()
print("  Thong ke label:")
for r in db[FINAL_COLL].aggregate([{"$group": {"_id": "$label", "count": {"$sum": 1}}}]):
    print("    " + str(r["_id"]) + ": " + str(r["count"]))

print()
print("  5 mau moi nhat:")
for doc in db[FINAL_COLL].find().limit(5):
    ts   = doc.get("timestamp", "")
    lbl  = doc.get("label", "")
    conf = doc.get("confidence", "")
    bpm  = doc.get("bpm", "")
    sp2  = doc.get("spo2", "")
    bt   = doc.get("body_temp", "")
    gsr  = doc.get("gsr_adc", "")
    print("    ts=" + str(ts) + " bpm=" + str(bpm) + " spo2=" + str(sp2) +
          " body_temp=" + str(bt) + " gsr=" + str(gsr) +
          " label=" + str(lbl) + " conf=" + str(conf))

print()
print("=" * 60)
print("  HE THONG 4 COLLECTIONS + VIEW")
print("=" * 60)
for coll_name in db.list_collection_names():
    c = db[coll_name]
    total = c.count_documents({})
    s = c.find_one() or {}
    fields = sorted([k for k in s.keys() if k != "_id"])
    if coll_name == FINAL_COLL:
        role = "KET QUA CUOI CUNG (VIEW - tu dong update)"
    elif coll_name == "datalake_raw":
        role = "DATA LAKE (raw + metadata, vinh vien)"
    elif coll_name == "realtime_health_data":
        role = "DATAWAREHOUSE (12 features, chua gan nhan)"
    elif coll_name == "training_health_data":
        role = "TRAINING DATA (co label, huan luyen ML)"
    else:
        role = "KHAC"
    print()
    print("  [" + coll_name + "]  " + role)
    print("    Docs: " + str(total))
    print("    Fields: " + str(fields))

client.close()
print()
print("=" * 60)
print("  HOAN TAT!")
print("=" * 60)
