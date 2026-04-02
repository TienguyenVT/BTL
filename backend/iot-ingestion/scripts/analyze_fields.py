# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

print("=== RAW_PAYLOAD fields (datalake_raw) ===")
coll = db["datalake_raw"]
sample = coll.find_one()
raw = sample.get("raw_payload", {})
sensor = sample.get("sensor", {})
print("raw_payload fields:")
for k, v in raw.items():
    print("  raw_payload." + str(k) + ": " + str(v))
print("sensor fields:")
for k, v in sensor.items():
    print("  sensor." + str(k) + ": " + str(v))

print()
print("=== TRAINING DATA fields (training_health_data) ===")
td = db["training_health_data"]
td_sample = td.find_one()
if td_sample:
    for k in sorted(td_sample.keys()):
        if k != "_id":
            print("  " + str(k) + ": " + str(td_sample[k]))

print()
print("=== REALTIME_HEALTH_DATA fields ===")
rt = db["realtime_health_data"]
rt_sample = rt.find_one()
if rt_sample:
    for k in sorted(rt_sample.keys()):
        if k != "_id":
            print("  " + str(k) + ": " + str(rt_sample[k]))

print()
print("=== PREDICTION sample (datalake_raw, 5 docs) ===")
for doc in coll.find({"prediction": {"$ne": None}}).limit(5):
    pred = doc.get("prediction", {})
    ts = doc.get("timestamp", "")
    dev = doc.get("device_id", "")
    sens = doc.get("sensor", {})
    print("  timestamp=" + str(ts) + "  device=" + str(dev))
    print("    prediction.label=" + str(pred.get("label")) + "  confidence=" + str(pred.get("confidence")))
    print("    sensor: " + str(sens))

print()
print("=== RAW_PAYLOAD full sample ===")
for k, v in raw.items():
    print("  raw_payload." + str(k) + ": " + str(v))

print()
print("=== Check room_temp / humidity fields across collections ===")
for coll_name in db.list_collection_names():
    c = db[coll_name]
    s = c.find_one() or {}
    room_keys = [k for k in s.keys() if "room" in k.lower() or "humid" in k.lower() or "temp" in k.lower()]
    print("  " + coll_name + ": " + str(room_keys) if room_keys else "  " + coll_name + ": (khong co room/humid fields)")

client.close()
