# -*- coding: utf-8 -*-
"""
Fix final_result VIEW (v2):
  1. Drop final_result cu (collection hoac view)
  2. Tao VIEW moi chi voi sensor + prediction
  3. Thong ke ket qua

final_result VIEW chi chua:
  device_id, mac_address, timestamp, ingested_at,
  bpm, spo2, body_temp, gsr_adc,
  room_temp, humidity,
  label, confidence
"""
import os
import sys
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
print("  FIX final_result VIEW (v2)")
print("  Chi luu: sensor + prediction, KHONG co engineered features")
print("=" * 60)

# ── Step 1: Inspect datalake_raw schema ─────────────────────
print("\n[0] Kiem tra datalake_raw schema hien tai...")
datalake_sample = db["datalake_raw"].find_one()
if datalake_sample:
    sensor = datalake_sample.get("sensor", {})
    features = datalake_sample.get("features", {})
    pred = datalake_sample.get("prediction", {})
    print("    sensor fields : " + str(sorted(sensor.keys())))
    print("    features fields: " + str(sorted(features.keys())))
    print("    prediction fields: " + str(sorted(pred.keys()) if pred else "null"))
else:
    print("    datalake_raw is EMPTY! Khong co data de tao VIEW.")
    client.close()
    sys.exit(1)

# ── Step 2: Drop existing final_result ──────────────────────
print("\n[1] Xoa final_result cu (neu co)...")
existing = db.list_collection_names()
if FINAL_COLL in existing:
    db[FINAL_COLL].drop()
    print("    Da xoa final_result cu.")
else:
    print("    Chua co final_result, bo qua.")

# ── Step 3: Build VIEW pipeline ─────────────────────────────
# KHONG con engineered features trong VIEW
pipeline = [
    # Chi lay docs da co prediction (da duoc gan nhan)
    {"$match": {
        "prediction.label": {"$exists": True, "$ne": None}
    }},
    # Flatten sensor + prediction -> top-level fields
    {"$addFields": {
        # 4 core sensor fields
        "bpm":         "$sensor.bpm",
        "spo2":        "$sensor.spo2",
        "body_temp":   "$sensor.body_temp",
        "gsr_adc":     "$sensor.gsr_adc",
        # 2 DHT11 fields (Node-RED luu la dht11_room_temp / dht11_humidity)
        "room_temp":   "$sensor.dht11_room_temp",
        "humidity":    "$sensor.dht11_humidity",
        # Prediction
        "label":       "$prediction.label",
        "confidence":  "$prediction.confidence",
        # mac_address: top-level trong datalake_raw (Node-RED v5+)
        # fallback sang raw_payload.mac_address neu can (backward compat)
        "mac_address": {
            "$ifNull": [
                "$mac_address",
                {"$ifNull": ["$raw_payload.mac_address", None]}
            ]
        },
    }},
    # Project chi cac fields can thiet — KHONG co engineered features
    {"$project": {
        "_id": 0,
        # Time + device
        "timestamp":    1,
        "device_id":   1,
        "mac_address": 1,
        "ingested_at": 1,
        "source":       1,
        "data_quality": 1,
        "schema_version": 1,
        # 4 core sensor
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
    }},
    # Sort: moi nhat truoc (cho query default)
    {"$sort": {"ingested_at": -1}},
]

db.create_collection(FINAL_COLL, viewOn="datalake_raw", pipeline=pipeline)
print("\n[2] Da tao VIEW '" + FINAL_COLL + "' (view tren datalake_raw).")
print("    Chi chua: bpm, spo2, body_temp, gsr_adc, room_temp, humidity, label, confidence")
print("    KHONG con: bpm_spo2_ratio, temp_gsr_interaction, bpm_temp_product, ...")

# ── Step 4: Verify VIEW ─────────────────────────────────────
total = db[FINAL_COLL].count_documents({})
print("\n[3] Tong docs trong VIEW: " + str(total))

if total == 0:
    print("    WARNING: VIEW co 0 docs!")
    print("    Nguyen nhan: datalake_raw chua co docs nao co prediction.label.")
    print("    Kiem tra: MQTT dang chay? Python /predict dang chay?")
    has_pred = db["datalake_raw"].count_documents({"prediction.label": {"$exists": True, "$ne": None}})
    print("    datalake_raw docs co prediction.label: " + str(has_pred))
else:
    print("\n[4] Thong ke label:")
    for r in db[FINAL_COLL].aggregate([{"$group": {"_id": "$label", "count": {"$sum": 1}}}]):
        print("    " + str(r["_id"]) + ": " + str(r["count"]))

    sample = db[FINAL_COLL].find_one()
    if sample:
        print("\n[5] Mau document (khong _id):")
        for k, v in sorted(sample.items()):
            if k == "_id":
                continue
            val_str = str(v)[:80]
            print("    " + str(k) + ": " + val_str)

# ── Step 5: Summary of all collections ──────────────────────
print("\n" + "=" * 60)
print("  HE THONG COLLECTIONS")
print("=" * 60)
for coll_name in db.list_collection_names():
    try:
        c = db[coll_name]
        total = c.count_documents({})
        s = c.find_one() or {}
        fields = sorted([k for k in s.keys() if k != "_id"])
        if coll_name == FINAL_COLL:
            role = ">>> KET QUA CUOI (VIEW - chi sensor + prediction)"
        elif coll_name == "datalake_raw":
            role = "DATA LAKE (raw + metadata + features, vinh vien)"
        elif coll_name == "realtime_health_data":
            role = "DATAWAREHOUSE (chi sensor, chua gan nhan)"
        elif coll_name == "training_health_data":
            role = "TRAINING DATA"
        else:
            role = ""
        print("\n  [" + coll_name + "]  " + role)
        print("    Docs: " + str(total))
        print("    Fields: " + str(fields))
    except Exception as e:
        print("\n  [" + coll_name + "]  ERROR: " + str(e))

client.close()
print("\n" + "=" * 60)
print("  HOAN TAT! Hay deploy Node-RED flow va chay script nay.")
print("  Sau do xoa sessions collection: db.sessions.drop()")
print("  Hoac chay: python scripts/clear_sessions.py")
print("=" * 60)
