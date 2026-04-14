# -*- coding: utf-8 -*-
"""
Fix final_result VIEW:
  1. Drop final_result cu (collection hoac view)
  2. Tao VIEW moi voi schema chinh xac khop voi datalake_raw hien tai
  3. Thong ke ket qua

Lua y:
  - VIEW tu dong reflect thay doi trong datalake_raw
  - Khong can chay lai script nay khi co data moi
  - Chi can chay lai neu muon thay doi pipeline
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
print("  FIX final_result VIEW")
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
# Chu y: datalake_raw co sensor.dht11_room_temp, sensor.dht11_humidity
# View se flatten cac fields nay thanh room_temp, humidity
pipeline = [
    # Chi lay docs da co prediction (da duoc gan nhan)
    {"$match": {
        "prediction.label": {"$exists": True, "$ne": None}
    }},
    # Flatten sensor subdocument -> top-level fields
    {"$addFields": {
        # 4 core sensor fields
        "bpm":         "$sensor.bpm",
        "spo2":        "$sensor.spo2",
        "body_temp":   "$sensor.body_temp",
        "gsr_adc":     "$sensor.gsr_adc",
        # 2 DHT11 fields (Node-RED luu la dht11_room_temp / dht11_humidity)
        "room_temp":   "$sensor.dht11_room_temp",
        "humidity":    "$sensor.dht11_humidity",
        # Full features (10 fields)
        "bpm_spo2_ratio":              "$features.bpm_spo2_ratio",
        "temp_gsr_interaction":        "$features.temp_gsr_interaction",
        "bpm_temp_product":            "$features.bpm_temp_product",
        "spo2_gsr_ratio":             "$features.spo2_gsr_ratio",
        "bpm_deviation":              "$features.bpm_deviation",
        "temp_deviation":             "$features.temp_deviation",
        "gsr_deviation":             "$features.gsr_deviation",
        "physiological_stress_index": "$features.physiological_stress_index",
        "heat_index":                 "$features.heat_index",
        "comfort_index":              "$features.comfort_index",
        # Prediction
        "label":       "$prediction.label",
        "confidence":  "$prediction.confidence",
    }},
    # Project chi cac fields can thiet
    {"$project": {
        "_id": 0,
        # Time + device
        "timestamp":    1,
        "device_id":   1,
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
        # 10 engineered features
        "bpm_spo2_ratio":              1,
        "temp_gsr_interaction":        1,
        "bpm_temp_product":            1,
        "spo2_gsr_ratio":             1,
        "bpm_deviation":              1,
        "temp_deviation":             1,
        "gsr_deviation":             1,
        "physiological_stress_index": 1,
        "heat_index":                 1,
        "comfort_index":              1,
        # Label + confidence
        "label":       1,
        "confidence":  1,
        # Backward compat: mac_address from raw_payload if exists
        "mac_address": "$raw_payload.mac_address",
    }},
    # Sort: moi nhat truoc (cho query default)
    {"$sort": {"ingested_at": -1}},
]

db.create_collection(FINAL_COLL, viewOn="datalake_raw", pipeline=pipeline)
print("\n[2] Da tao VIEW '" + FINAL_COLL + "' (view tren datalake_raw).")
print("    View tu dong reflect thay doi khi datalake_raw insert moi.")

# ── Step 4: Verify VIEW ─────────────────────────────────────
total = db[FINAL_COLL].count_documents({})
print("\n[3] Tong docs trong VIEW: " + str(total))

if total == 0:
    print("    WARNING: VIEW co 0 docs!")
    print("    Nguyen nhan: datalake_raw chua co docs nao co prediction.label.")
    print("    Kiem tra: MQTT dang chay? Python /predict dang chay?")
    # Check prediction
    has_pred = db["datalake_raw"].count_documents({"prediction.label": {"$exists": True, "$ne": None}})
    print("    datalake_raw docs co prediction.label: " + str(has_pred))
else:
    print("\n[4] Thong ke label:")
    for r in db[FINAL_COLL].aggregate([{"$group": {"_id": "$label", "count": {"$sum": 1}}}]):
        print("    " + str(r["_id"]) + ": " + str(r["count"]))

    # Sample
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
            role = ">>> KET QUA CUOI (VIEW)"
        elif coll_name == "datalake_raw":
            role = "DATA LAKE (Nguon chuan)"
        elif coll_name == "realtime_health_data":
            role = "DATAWAREHOUSE"
        elif coll_name == "training_health_data":
            role = "TRAINING DATA"
        else:
            role = ""
        print(f"\n  [{coll_name}]  {role}")
        print(f"    Docs: {total}")
        print(f"    Fields: {fields}")
    except Exception as e:
        print(f"\n  [{coll_name}]  ERROR: {e}")

client.close()
print("\n" + "=" * 60)
print("  HOAN TAT! Hay restart backend Spring Boot.")
print("  Sau do xoa sessions collection: db.sessions.drop()")
print("  Hoac chay: python scripts/clear_sessions.py")
print("=" * 60)
