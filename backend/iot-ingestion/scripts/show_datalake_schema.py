# -*- coding: utf-8 -*-
"""Hien thi day du schema + mau document cua datalake_raw."""
import os, sys, json
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from bson.json_util import dumps

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
coll = db["datalake_raw"]

print("=" * 60)
print("  DATALAKE_RAW — SCHEMA & MẪU DOCUMENT")
print("=" * 60)

# Tong
total = coll.count_documents({})
print("\nTong docs: " + str(total))

# Indexes
print("\nIndexes:")
for idx in coll.list_indexes():
    print("  " + idx["name"] + ": " + str(idx["key"]))

# Fields mapping
FIELDS = {
    "source":                  "Nguon du lieu: mqtt_esp32 | rest_api | csv_batch | manual",
    "source_topic":            "MQTT topic / API endpoint goc",
    "device_id":              "ID thiet bi gui du lieu (ESP32 MAC / serial)",
    "timestamp":               "Unix ms timestamp tu ESP32 (thoi gian thiet bi gui)",
    "mode":                   "ESP32 operation mode (int, null neu khong co)",
    "raw_payload":            "Tat ca truong nhan duoc tu MQTT — GOC, KHONG CHINH SUA",
    "  raw_payload.bpm":      "Nhịp tim goc (tu ESP32)",
    "  raw_payload.spo2":     "SpO2 goc (tu ESP32)",
    "  raw_payload.body_temp":"Nhiet do co the goc (tu ESP32)",
    "  raw_payload.gsr_adc":  "GSR ADC goc (tu ESP32)",
    "  raw_payload.device_id":"Device ID goc",
    "  raw_payload.timestamp": "Timestamp goc (Unix ms)",
    "  raw_payload.mode":     "Mode goc",
    "sensor":                 "Gia tri sensor DA DUOC NORMALIZE (sau outlier rejection)",
    "  sensor.bpm":           "BPM sau khi validate",
    "  sensor.spo2":          "SpO2 sau khi validate",
    "  sensor.body_temp":     "Body temp sau khi validate",
    "  sensor.gsr_adc":       "GSR ADC sau khi validate",
    "features":               "8 engineered features tu pipeline Node-RED",
    "  features.bpm_spo2_ratio":            "BPM / SpO2",
    "  features.temp_gsr_interaction":      "Body_temp * GSR",
    "  features.bpm_temp_product":          "BPM * Body_temp",
    "  features.spo2_gsr_ratio":             "SpO2 / GSR",
    "  features.bpm_deviation":             "|BPM - median(BPM)|",
    "  features.temp_deviation":             "|Body_temp - median(Body_temp)|",
    "  features.gsr_deviation":             "|GSR - median(GSR)|",
    "  features.physiological_stress_index":  "Composite stress score",
    "prediction":             "Ket qua ML tu /predict endpoint (null neu chua predict)",
    "  prediction.label":     "Nhan du doan: normal | stress | relaxation",
    "  prediction.confidence": "Do chinh xac (0.0 – 1.0)",
    "data_quality":           "Chat luong: raw | normalized | outlier_rejected",
    "schema_version":         "Phien ban schema (hien tai: 1.0)",
    "ingested_at":            "Server timestamp luc nhan duoc MQTT message",
    "processing_latency_ms":  "Do tre tu luc ESP32 gui -> luc luu MongoDB (ms)",
    "_id":                    "MongoDB ObjectId (auto-gen, khong can quan tam)",
}

print("\nTat ca truong du lieu trong datalake_raw:")
print("-" * 60)
for f, desc in FIELDS.items():
    indent = "  " if f.startswith("  ") else "  "
    print(indent + f)
    print("       Mo ta: " + desc)

# Mau document (JSON dep)
print("\n" + "=" * 60)
print("  MẪU DOCUMENT (sample #1)")
print("=" * 60)
sample = coll.find_one()
if sample:
    print(dumps(sample, indent=2, ensure_ascii=False))

# Thong ke
print("\n" + "=" * 60)
print("  THONG KE")
print("=" * 60)
print("\nTheo source:")
for src, cnt in coll.aggregate([{"$group": {"_id": "$source", "count": {"$sum": 1}}}]):
    print("  " + str(src) + ": " + str(cnt))

print("\nTheo data_quality:")
for dq, cnt in coll.aggregate([{"$group": {"_id": "$data_quality", "count": {"$sum": 1}}}]):
    print("  " + str(dq) + ": " + str(cnt))

print("\nTheo prediction.label:")
for lbl, cnt in coll.aggregate([{"$group": {"_id": "$prediction.label", "count": {"$sum": 1}}}]):
    print("  " + str(lbl) + ": " + str(cnt))

client.close()
