# -*- coding: utf-8 -*-
"""
Thiet ke & khoi tao datalake_raw (Data Lake dung chuan).
Datalake khac raw_sensor o cho:
  1. Khong co TTL — luu vinh vien
  2. Co metadata phong phu: source, schema_version, data_quality,
     processing_latency_ms, ingested_at
  3. Co cau truc phan lop: raw_payload (goc), sensor (normalize),
     features (engineered), prediction (ket qua ML)
  4. Co nhieu nguon: mqtt_esp32, rest_api, csv_batch, ...
  5. Co schema versioning de track thay doi the thoi gian
"""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")
DATALAKE_COLL    = "datalake_raw"
RAW_SENSOR_COLL  = "raw_sensor"

EXPECTED_DATALAKE_FIELDS = {
    "source", "source_topic", "device_id", "timestamp",
    "mode", "raw_payload", "sensor", "features",
    "prediction", "data_quality", "schema_version",
    "ingested_at", "processing_latency_ms"
}


def init_datalake():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    print("=" * 60)
    print("  DATA LAKE INIT: datalake_raw")
    print("=" * 60)

    # ── 1. Kiem tra hien trang ───────────────────────────────
    collections = db.list_collection_names()
    print("\n[1] Collections hien tai:")
    for c in collections:
        n = db[c].count_documents({})
        print("    " + c + ": " + str(n) + " docs")

    coll = db[DATALAKE_COLL]

    # ── 2. Tao indexes (khong co TTL) ────────────────────────
    print("\n[2] Tao indexes cho datalake_raw (khong co TTL):")
    indexes = [
        ({"source": ASCENDING},                            "idx_source"),
        ({"timestamp": DESCENDING},                        "idx_timestamp"),
        ({"device_id": ASCENDING, "timestamp": DESCENDING},"idx_device_timestamp"),
        ({"data_quality": ASCENDING},                       "idx_data_quality"),
        ({"prediction.label": ASCENDING},                   "idx_prediction_label"),
        ({"ingested_at": DESCENDING},                      "idx_ingested_at"),
        ({"processing_latency_ms": ASCENDING},              "idx_processing_latency"),
    ]
    for keys, name in indexes:
        try:
            coll.create_index(keys, name=name)
            print("    [OK] " + name)
        except Exception as e:
            print("    [SKIP] " + name + ": " + str(e))

    # ── 3. Hien thi schema ───────────────────────────────────
    print("\n[3] Schema datalake_raw (du kien):")
    schema_desc = {
        "source":                   "Nguon: mqtt_esp32 | rest_api | csv_batch | manual",
        "source_topic":             "MQTT topic / API endpoint goc",
        "device_id":               "ID thiet bi gui du lieu",
        "timestamp":               "Unix ms timestamp tu ESP32",
        "mode":                   "ESP32 operation mode (null neu khong co)",
        "raw_payload":             "Tat ca truong nhan tu MQTT (goc, untouched)",
        "sensor":                 "Normalized: bpm, spo2, body_temp, gsr_adc",
        "features":               "8 engineered features tu pipeline",
        "prediction":             "Ket qua ML: {label, confidence} | null",
        "data_quality":           "raw | normalized | outlier_rejected",
        "schema_version":         "Version cua schema (hien tai: 1.0)",
        "ingested_at":            "Server timestamp khi nhan duoc message",
        "processing_latency_ms":  "Do tre tu ESP32 gui den luc luu (ms)",
    }
    for field in sorted(EXPECTED_DATALAKE_FIELDS):
        print("    " + field)
        print("        -> " + schema_desc.get(field, ""))

    # ── 4. Migration raw_sensor -> datalake_raw ──────────────
    print("\n[4] Migration raw_sensor -> datalake_raw:")
    if RAW_SENSOR_COLL in collections:
        count_raw = db[RAW_SENSOR_COLL].count_documents({})
        print("    raw_sensor: " + str(count_raw) + " docs")
        if count_raw > 0:
            # Migrate all at once (bulk)
            pipeline = [
                {"$project": {
                    "source":          {"$literal": "mqtt_esp32"},
                    "source_topic":    {"$literal": "ptit/health/data"},
                    "device_id":       "$device_id",
                    "timestamp":       "$timestamp",
                    "mode":            "$mode",
                    "raw_payload":     "$$ROOT",
                    "sensor": {
                        "bpm":       "$bpm",
                        "spo2":      "$spo2",
                        "body_temp": "$body_temp",
                        "gsr_adc":   "$gsr_adc",
                    },
                    "features":        {},
                    "prediction":      None,
                    "data_quality":   {"$literal": "raw"},
                    "schema_version": {"$literal": "1.0"},
                    "ingested_at":    "$ingested_at",
                    "processing_latency_ms": None,
                }},
                {"$out": DATALAKE_COLL + "_staging"},
            ]
            try:
                db[RAW_SENSOR_COLL].aggregate(pipeline)
                # Swap: rename staging -> datalake_raw
                db[DATALAKE_COLL].drop()
                db[DATALAKE_COLL + "_staging"].rename(DATALAKE_COLL)
                print("    [OK] Da migrate " + str(count_raw) + " docs vao datalake_raw")
            except Exception as e:
                print("    [ERR] Migration failed: " + str(e))
                print("    [INFO] Thu migrate thu cong...")
                migrated = 0
                for doc in db[RAW_SENSOR_COLL].find():
                    dl_doc = {
                        "source":          "mqtt_esp32",
                        "source_topic":    "ptit/health/data",
                        "device_id":      doc.get("device_id", "unknown"),
                        "timestamp":      doc.get("timestamp"),
                        "mode":           doc.get("mode"),
                        "raw_payload":    {
                            "bpm":       doc.get("bpm"),
                            "spo2":      doc.get("spo2"),
                            "body_temp": doc.get("body_temp"),
                            "gsr_adc":   doc.get("gsr_adc"),
                            "device_id": doc.get("device_id"),
                            "timestamp": doc.get("timestamp"),
                            "mode":      doc.get("mode"),
                        },
                        "sensor": {
                            "bpm":       doc.get("bpm"),
                            "spo2":      doc.get("spo2"),
                            "body_temp": doc.get("body_temp"),
                            "gsr_adc":   doc.get("gsr_adc"),
                        },
                        "features":        {},
                        "prediction":      None,
                        "data_quality":   "raw",
                        "schema_version": "1.0",
                        "ingested_at":    doc.get("ingested_at", datetime.now(timezone.utc)),
                        "processing_latency_ms": None,
                    }
                    coll.insert_one(dl_doc)
                    migrated += 1
                print("    [OK] Da migrate " + str(migrated) + " docs (thu cong)")

            # Xoa TTL index tren raw_sensor
            try:
                db[RAW_SENSOR_COLL].drop_index("ingested_at_1")
                print("    [OK] Da xoa TTL index khoi raw_sensor")
            except:
                print("    [SKIP] TTL index khong ton tai tren raw_sensor")
    else:
        print("    raw_sensor khong ton tai, bo qua.")

    # ── 5. Hien thi mau ───────────────────────────────────────
    print("\n[5] Mau document datalake_raw:")
    sample = coll.find_one()
    if sample:
        # Loai bo _id de hien thi
        for k, v in sample.items():
            if k != "_id":
                print("    " + str(k) + ": " + str(v)[:100])
    else:
        print("    Collection trong.")

    total = coll.count_documents({})
    print("\n    Tong docs trong datalake_raw: " + str(total))

    client.close()
    print("\n" + "=" * 60)
    print("  HOAN TAT!")
    print("=" * 60)


if __name__ == "__main__":
    init_datalake()
