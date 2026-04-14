# -*- coding: utf-8 -*-
"""
Sinh du lieu synthetic cho 9 thiet bi moi (tru macAddress).
- Moi thiet bi: 500 mau data
- Timestamp phan bo deu tu 24/3/2026 - 12/4/2026
- Toi da 20 phien do / thiet bi
- Du lieu sensor ngau nhien nhung hop ly thuc te
- Insert vao datalake_raw (vi final_result la VIEW)
"""

import os
import sys
import random
import math
from datetime import datetime, timedelta, timezone
from bson import ObjectId

sys.path.insert(0, r"d:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"d:\Documents\BTL\backend\iot-ingestion\.env")

from pymongo import MongoClient
from pymongo.errors import BulkWriteError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
coll = db["datalake_raw"]

# ══════════════════════════════════════════════════════════════════════════════
# Cau hinh thiet bi
# ══════════════════════════════════════════════════════════════════════════════

# 9 MAC Address moi (ngoai tru esp32_iot_health_01 da co san)
NEW_DEVICES = [
    ("esp32_iot_health_02", "4a:b2:01:c3:4d:10"),
    ("esp32_iot_health_03", "2c:3e:5f:8a:1b:22"),
    ("esp32_iot_health_04", "1d:9c:3e:7f:0a:55"),
    ("esp32_iot_health_05", "8b:71:2d:6e:9f:33"),
    ("esp32_iot_health_06", "6a:54:8c:1e:3b:77"),
    ("esp32_iot_health_07", "3f:28:6d:4c:7a:88"),
    ("esp32_iot_health_08", "9c:63:1a:5f:8d:99"),
    ("esp32_iot_health_09", "5e:47:9b:2c:6f:44"),
    ("esp32_iot_health_10", "7b:85:3d:6a:1c:aa"),
]

SAMPLES_PER_DEVICE = 500
MAX_SESSIONS_PER_DEVICE = 20
SAMPLES_PER_SESSION_MIN = 15
SAMPLES_PER_SESSION_MAX = 40

# Khoang thoi gian: 24/3/2026 00:00:00 -> 12/4/2026 23:59:59
START_DATE = datetime(2026, 3, 24, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2026, 4, 12, 23, 59, 59, tzinfo=timezone.utc)

# Khoang thoi gian nghi giua cac phien (gap > 30 phut = phien moi)
SESSION_GAP_MINUTES = 30
SAMPLES_INTERVAL_SECONDS = 2

# ══════════════════════════════════════════════════════════════════════════════
# Khoang gia tri sensor hop ly thuc te
# ══════════════════════════════════════════════════════════════════════════════

# Baseline values cho moi thiet bi
DEVICE_BASELINES = {}
random.seed(42)  # De co tinh nham nhất quán


def init_device_baseline(device_id: str):
    """Khoi tao baseline cho 1 thiet bi - gia tri tam thoi."""
    DEVICE_BASELINES[device_id] = {
        "bpm": random.randint(65, 85),
        "spo2": random.randint(96, 99),
        "body_temp": round(random.uniform(36.2, 36.8), 1),
        "gsr_adc": random.randint(2000, 2400),
        "room_temp": round(random.uniform(24.0, 28.0), 1),
        "humidity": random.randint(45, 65),
    }


def gaussian_noise(value: float, std: float) -> float:
    """Them nhieu Gaussian."""
    return value + random.gauss(0, std)


def generate_sensor_values(device_id: str, label: str):
    """Sinh gia tri sensor hop ly dua tren label va baseline cua thiet bi."""
    baseline = DEVICE_BASELINES[device_id]

    if label == "Normal":
        bpm = int(gaussian_noise(baseline["bpm"], std=8))
        spo2 = round(gaussian_noise(baseline["spo2"], std=1.2), 1)
        body_temp = round(gaussian_noise(baseline["body_temp"], std=0.15), 1)
        gsr_adc = int(gaussian_noise(baseline["gsr_adc"], std=100))
    elif label == "Stressed":
        bpm = int(gaussian_noise(baseline["bpm"] + 20, std=12))
        spo2 = round(gaussian_noise(baseline["spo2"] - 1.5, std=1.5), 1)
        body_temp = round(gaussian_noise(baseline["body_temp"] + 0.3, std=0.2), 1)
        gsr_adc = int(gaussian_noise(baseline["gsr_adc"] - 400, std=150))
    else:  # Relaxed
        bpm = int(gaussian_noise(baseline["bpm"] - 10, std=6))
        spo2 = round(gaussian_noise(baseline["spo2"] + 0.5, std=0.8), 1)
        body_temp = round(gaussian_noise(baseline["body_temp"] - 0.1, std=0.1), 1)
        gsr_adc = int(gaussian_noise(baseline["gsr_adc"] + 200, std=80))

    # Gioi han trong khoang hop ly
    bpm = max(45, min(175, bpm))
    spo2 = max(85, min(100, spo2))
    body_temp = max(35.5, min(39.5, body_temp))
    gsr_adc = max(1000, min(2500, gsr_adc))

    room_temp = round(gaussian_noise(baseline["room_temp"], std=1.0), 1)
    room_temp = max(22.0, min(34.0, room_temp))

    humidity = int(gaussian_noise(baseline["humidity"], std=5))
    humidity = max(30, min(80, humidity))

    return {
        "bpm": bpm,
        "spo2": spo2,
        "body_temp": body_temp,
        "gsr_adc": gsr_adc,
        "room_temp": room_temp,
        "humidity": humidity,
    }


def compute_features(sensors: dict, baseline: dict) -> dict:
    """Tinh engineered features."""
    bpm = sensors["bpm"]
    spo2 = sensors["spo2"]
    body_temp = sensors["body_temp"]
    gsr_adc = sensors["gsr_adc"]
    room_temp = sensors["room_temp"]
    humidity = sensors["humidity"]

    bl_bpm = baseline["bpm"]
    bl_spo2 = baseline["spo2"]
    bl_temp = baseline["body_temp"]
    bl_gsr = baseline["gsr_adc"]

    # Features
    bpm_spo2_ratio = round(bpm / max(spo2, 1), 6)
    temp_gsr_interaction = round(body_temp * gsr_adc / 10000, 6)
    bpm_temp_product = round(bpm * body_temp, 6)
    spo2_gsr_ratio = round(spo2 / max(gsr_adc, 1) * 1000, 6)
    bpm_deviation = round(bpm - bl_bpm, 6)
    temp_deviation = round(body_temp - bl_temp, 6)
    gsr_deviation = round(gsr_adc - bl_gsr, 6)
    physiological_stress_index = round((gsr_adc - bl_gsr) / 1500, 6)
    heat_index = round((room_temp - 20) * 0.3 + (humidity - 50) * 0.1, 2)
    comfort_index = round(
        max(0, min(1,
            1.0
            - abs(room_temp - 25) * 0.05
            - abs(humidity - 50) * 0.01
            - max(0, body_temp - 37.5) * 0.1
        )),
        2
    )

    return {
        "bpm_spo2_ratio": bpm_spo2_ratio,
        "temp_gsr_interaction": temp_gsr_interaction,
        "bpm_temp_product": bpm_temp_product,
        "spo2_gsr_ratio": spo2_gsr_ratio,
        "bpm_deviation": bpm_deviation,
        "temp_deviation": temp_deviation,
        "gsr_deviation": gsr_deviation,
        "physiological_stress_index": physiological_stress_index,
        "heat_index": heat_index,
        "comfort_index": comfort_index,
    }


def compute_prediction(sensors: dict, features: dict) -> tuple:
    """Xac dinh label va confidence dua tren sensor + features."""
    bpm = sensors["bpm"]
    spo2 = sensors["spo2"]
    body_temp = sensors["body_temp"]
    stress_idx = features["physiological_stress_index"]

    score = 0.0

    if 60 <= bpm <= 90:
        score += 1
    elif 50 <= bpm < 60 or 90 < bpm <= 100:
        score += 0.5
    elif 40 <= bpm < 50 or 100 < bpm <= 110:
        score += 0.2

    if spo2 >= 96:
        score += 1
    elif 94 <= spo2 < 96:
        score += 0.6
    elif 90 <= spo2 < 94:
        score += 0.3

    if 36.0 <= body_temp <= 37.0:
        score += 1
    elif 35.5 <= body_temp < 36.0 or 37.0 < body_temp <= 37.5:
        score += 0.6
    elif 37.5 < body_temp <= 38.0:
        score += 0.3

    if -0.2 <= stress_idx <= 0.2:
        score += 1
    elif stress_idx < -0.2:
        score += 0.3
    else:
        score += 0.8

    total_score = score / 4.0
    if total_score >= 0.75:
        label = "Normal"
        confidence = round(min(0.95, 0.65 + total_score * 0.25 + random.uniform(0, 0.1)), 4)
    elif total_score < 0.45:
        label = "Stressed"
        confidence = round(min(0.90, 0.55 + (0.5 - total_score) * 0.5 + random.uniform(0, 0.1)), 4)
    else:
        label = "Relaxed"
        confidence = round(min(0.88, 0.60 + total_score * 0.25 + random.uniform(0, 0.1)), 4)

    return label, confidence


def generate_sessions(device_id: str, num_sessions: int) -> list:
    """Phan bo cac phien do trong khoang thoi gian."""
    total_seconds = int((END_DATE - START_DATE).total_seconds())

    available_gaps = total_seconds - (num_sessions * SAMPLES_PER_SESSION_MAX * SAMPLES_INTERVAL_SECONDS)
    if available_gaps < 0:
        available_gaps = total_seconds // 2

    gap_size = available_gaps // (num_sessions + 1)
    sessions = []

    current_ts = START_DATE + timedelta(seconds=random.randint(0, gap_size // 2))

    for i in range(num_sessions):
        num_samples = SAMPLES_PER_DEVICE // num_sessions
        if i < SAMPLES_PER_DEVICE % num_sessions:
            num_samples += 1

        session_start = current_ts
        session_end = session_start + timedelta(seconds=num_samples * SAMPLES_INTERVAL_SECONDS)

        sessions.append((session_start, session_end))

        if i < num_sessions - 1:
            gap = gap_size + random.randint(-gap_size // 4, gap_size // 4)
            current_ts = session_end + timedelta(seconds=max(SESSION_GAP_MINUTES * 60, gap))

    return sessions


def build_document(device_id: str, mac_address: str, ts_dt: datetime, sensors: dict, features: dict, label: str, confidence: float) -> dict:
    """Build 1 document theo cau truc datalake_raw."""
    timestamp_str = ts_dt.strftime("%Y:%m:%d - %H:%M:%S")
    ingested_str = ts_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    return {
        "source": "mqtt_esp32",
        "source_topic": "ptit/health/data",
        "device_id": device_id,
        "timestamp": timestamp_str,
        "mode": 2,
        "raw_payload": {
            "device_id": device_id,
            "timestamp": timestamp_str,
            "mode": 2,
            "bpm": sensors["bpm"],
            "spo2": sensors["spo2"],
            "body_temp": sensors["body_temp"],
            "gsr_adc": sensors["gsr_adc"],
            "dht11_room_temp": sensors["room_temp"],
            "humidity": sensors["humidity"],
        },
        "sensor": {
            "bpm": sensors["bpm"],
            "spo2": sensors["spo2"],
            "body_temp": sensors["body_temp"],
            "gsr_adc": sensors["gsr_adc"],
            "dht11_room_temp": sensors["room_temp"],
            "humidity": sensors["humidity"],
        },
        "features": {
            "bpm_spo2_ratio": features["bpm_spo2_ratio"],
            "temp_gsr_interaction": features["temp_gsr_interaction"],
            "bpm_temp_product": features["bpm_temp_product"],
            "spo2_gsr_ratio": features["spo2_gsr_ratio"],
            "bpm_deviation": features["bpm_deviation"],
            "temp_deviation": features["temp_deviation"],
            "gsr_deviation": features["gsr_deviation"],
            "physiological_stress_index": features["physiological_stress_index"],
            "heat_index": features["heat_index"],
            "comfort_index": features["comfort_index"],
        },
        "prediction": {
            "label": label,
            "confidence": confidence,
        },
        "data_quality": "raw",
        "schema_version": "1.1",
        "ingested_at": ts_dt,
        "processing_latency_ms": random.uniform(10, 100),
        "mac_address": mac_address,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  SINH DU LIEU SYNTHETIC - 9 THIET BI MOI")
    print("=" * 70)
    print(f"\nThoi gian: {START_DATE.strftime('%Y-%m-%d')} -> {END_DATE.strftime('%Y-%m-%d')}")
    print(f"Mau/thiet bi: {SAMPLES_PER_DEVICE}")
    print(f"Toi da phien/thiet bi: {MAX_SESSIONS_PER_DEVICE}")
    print()

    # Seed random
    random.seed(datetime.now().microsecond)

    all_documents = []

    for device_id, mac_address in NEW_DEVICES:
        print(f"  Tao du lieu cho: {device_id} ({mac_address})")

        # Khoi tao baseline
        init_device_baseline(device_id)
        baseline = DEVICE_BASELINES[device_id]

        # So phien: 12-20
        num_sessions = random.randint(12, MAX_SESSIONS_PER_DEVICE)

        # Phan bo thoi gian
        sessions = generate_sessions(device_id, num_sessions)

        # Label cho moi phien
        labels_pool = []
        for _ in range(num_sessions):
            labels_pool.append(random.choices(["Normal", "Stressed", "Relaxed"], weights=[0.60, 0.25, 0.15], k=1)[0])

        # Sinh documents
        for session_idx, (session_start, session_end) in enumerate(sessions):
            session_label = labels_pool[session_idx]
            num_samples = SAMPLES_PER_DEVICE // num_sessions
            if session_idx < SAMPLES_PER_DEVICE % num_sessions:
                num_samples += 1

            session_duration = num_samples * SAMPLES_INTERVAL_SECONDS

            for i in range(num_samples):
                ts_offset = i * SAMPLES_INTERVAL_SECONDS + random.randint(-1, 1)
                ts_dt = session_start + timedelta(seconds=ts_offset)

                if ts_dt > END_DATE:
                    ts_dt = END_DATE

                sensors = generate_sensor_values(device_id, session_label)
                features = compute_features(sensors, baseline)
                label, confidence = compute_prediction(sensors, features)

                doc = build_document(device_id, mac_address, ts_dt, sensors, features, label, confidence)
                all_documents.append(doc)

        print(f"    -> {num_sessions} phien, {num_samples} mau/phien")

    # Ghi vao MongoDB
    print(f"\n[Dang ghi {len(all_documents)} documents vao datalake_raw...]")

    try:
        result = coll.insert_many(all_documents, ordered=False)
        inserted = len(result.inserted_ids)
        print(f"  -> Da ghi {inserted} documents thanh cong!")
    except BulkWriteError as bwe:
        inserted = len(all_documents) - len(bwe.details.get('writeErrors', []))
        print(f"  -> Da ghi {inserted} documents (co {len(bwe.details.get('writeErrors', []))} loi)")
        if bwe.details.get('writeErrors'):
            print(f"  Loi dau tien: {bwe.details['writeErrors'][0]}")

    # Thong ke cuoi cung
    total = coll.count_documents({})
    unique_devices = coll.distinct("device_id")
    view_total = db["final_result"].count_documents({})
    view_devices = db["final_result"].distinct("device_id")

    print(f"\n{'=' * 70}")
    print(f"  Thong ke datalake_raw:")
    print(f"    Tong documents: {total}")
    print(f"    Tong thiet bi: {len(unique_devices)}")
    print(f"  Thong ke final_result (VIEW):")
    print(f"    Tong documents: {view_total}")
    print(f"    Tong thiet bi: {len(view_devices)}")
    print("=" * 70)

    # Chi tiet tung thiet bi
    print(f"\nChi tiet thiet bi trong final_result:")
    print("-" * 60)
    for dev in sorted(view_devices):
        count = db["final_result"].count_documents({"device_id": dev})
        latest = db["final_result"].find_one({"device_id": dev}, sort=[("timestamp", -1)])
        earliest = db["final_result"].find_one({"device_id": dev}, sort=[("timestamp", 1)])
        if latest and earliest:
            print(f"  {dev:<25} | {count:>5} mau | {earliest['timestamp'][:16]} -> {latest['timestamp'][:16]}")
    print("-" * 60)

    client.close()


if __name__ == "__main__":
    main()
