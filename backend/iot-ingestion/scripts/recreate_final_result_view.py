# -*- coding: utf-8 -*-
"""
Tao lai final_result VIEW (chi sensor + prediction, KHONG co engineered features).
View se tu dong reflect thay doi trong datalake_raw.

final_result VIEW chi chua:
  device_id, mac_address, timestamp, ingested_at,
  bpm, spo2, body_temp, gsr_adc,
  room_temp, humidity,
  label, confidence
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
print("  TAO / CAP NHAT final_result VIEW (v2)")
print("  Chi luu: sensor + prediction, KHONG co engineered features")
print("=" * 60)

# Xoa collection/view cu
existing = db.list_collection_names()
if FINAL_COLL in existing:
    db[FINAL_COLL].drop()
    print("[1] Da xoa " + FINAL_COLL + " cu.")
else:
    print("[1] Chua co " + FINAL_COLL + ", tiep tuc.")

# Tao VIEW moi chi voi sensor + prediction (khong co engineered features)
pipeline = [
    # Chi lay docs co prediction.label
    {"$match": {
        "prediction.label": {"$exists": True, "$ne": None}
    }},
    # Flatten sensor + prediction + device ra bac nhat
    {"$addFields": {
        # 4 sensor fields
        "bpm":        "$sensor.bpm",
        "spo2":      "$sensor.spo2",
        "body_temp": "$sensor.body_temp",
        "gsr_adc":   "$sensor.gsr_adc",
        # 2 DHT11 fields
        "room_temp":   "$sensor.dht11_room_temp",
        "humidity":    "$sensor.dht11_humidity",
        # Prediction
        "label":      "$prediction.label",
        "confidence": "$prediction.confidence",
        # Device identity
        "mac_address": "$mac_address",
    }},
    # Project chi cac fields can thiet — KHONG co engineered features
    {"$project": {
        "_id": 0,
        # Thoi gian + thiet bi
        "timestamp":   1,
        "device_id":   1,
        "mac_address": 1,
        "ingested_at": 1,
        "source":       1,
        "data_quality": 1,
        # 4 sensor
        "bpm":         1,
        "spo2":        1,
        "body_temp":   1,
        "gsr_adc":     1,
        # 2 DHT11
        "room_temp":   1,
        "humidity":    1,
        # Label + confidence
        "label":       1,
        "confidence":  1,
        "schema_version": 1,
    }},
    # Sort: moi nhat truoc
    {"$sort": {"ingested_at": -1}},
]

db.create_collection(FINAL_COLL, viewOn="datalake_raw", pipeline=pipeline)
print("[2] Da tao VIEW '" + FINAL_COLL + "' (view tren datalake_raw).")
print("    Chi chua: bpm, spo2, body_temp, gsr_adc, room_temp, humidity, label, confidence")
print("    KHONG con: bpm_spo2_ratio, temp_gsr_interaction, bpm_temp_product, ...")

# Verify
total = db[FINAL_COLL].count_documents({})
print()
print("[3] Tong docs trong view: " + str(total))

print()
print("[4] Thong ke label:")
for r in db[FINAL_COLL].aggregate([{"$group": {"_id": "$label", "count": {"$sum": 1}}}]):
    print("    " + str(r["_id"]) + ": " + str(r["count"]))

# Mau document
sample = db[FINAL_COLL].find_one()
if sample:
    print()
    print("[5] Mau document (khong _id):")
    for k, v in sorted(sample.items()):
        if k == "_id":
            continue
        print("    " + str(k) + ": " + str(v))

# Kiem tra DHT11 fields
print()
print("[6] Kiem tra DHT11 fields (datalake_raw):")
datalake_sample = db["datalake_raw"].find_one()
if datalake_sample:
    sensor = datalake_sample.get("sensor", {})
    print("    sensor fields: " + str(sorted(sensor.keys())))
    has_room = "dht11_room_temp" in sensor
    has_hum  = "dht11_humidity"  in sensor
    print("    co dht11_room_temp: " + str(has_room))
    print("    co dht11_humidity:  " + str(has_hum))

# He thong collections + view
print()
print("=" * 60)
print("  HE THONG MONGODB SAU CAP NHAT")
print("=" * 60)
for coll_name in db.list_collection_names():
    c = db[coll_name]
    total = c.count_documents({})
    s = c.find_one() or {}
    fields = sorted([k for k in s.keys() if k != "_id"])
    if coll_name == FINAL_COLL:
        role = "KET QUA CUOI CUNG (VIEW - chi sensor + prediction)"
    elif coll_name == "datalake_raw":
        role = "DATA LAKE (raw + metadata + features, vinh vien)"
    elif coll_name == "realtime_health_data":
        role = "DATAWAREHOUSE (chi sensor, chua gan nhan)"
    elif coll_name == "training_health_data":
        role = "TRAINING DATA"
    else:
        role = "KHAC"
    print()
    print("  [" + coll_name + "]  " + role)
    print("    Docs: " + str(total))
    print("    Fields: " + str(fields))

client.close()
print()
print("=" * 60)
print("  HOAN TAT! Hay deploy Node-RED flow va chay script nay.")
print("=" * 60)
