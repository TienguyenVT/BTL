# -*- coding: utf-8 -*-
"""
Sinh du lieu tong hop cho training ML model.

MUC DICH:
  Sinh 15000 mau (5000 Normal + 5000 Stress + 5000 Fever) cho cung 1 user.
  Ghi vao MongoDB realtime_health_data voi predicted_label=None / confidence=None
  de auto_label.py xu ly toan bo label + confidence.

CHINH SACH QUAN TRONG:
  1. Boundary overlap co y: tranh data leakage, model khong hoc theo rule boundaries.
  2. Double noise separation: distribution std nho (sinh ly) + sensor noise (ESP32).
  3. Timestamps randomized trong 21 ngay: tranh temporal artifact.
  4. auto_label.py xu ly label/confidence — generate script chi ghi raw data.

LIMITATION:
  Fever = 100% synthetic. Khi co du lieu Fever thuc (20-30 mau), uu tien retrain.
"""

import sys
import os
sys.path.insert(0, "C:/Documents/BTL/backend/iot-ingestion")

from dotenv import load_dotenv
load_dotenv("C:/Documents/BTL/backend/iot-ingestion/.env")

from pymongo import MongoClient
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")
COLLECTION_NAME = "realtime_health_data"

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Device
DEVICE_ID = "ESP32_SYNTHETIC"
# Base timestamp: 2026-01-01 00:00:00 UTC
BASE_TS_MS = int(datetime(2026, 1, 1).timestamp() * 1000)
# Timestamps randomized across 21 days
TIME_RANGE_MS = 21 * 24 * 3600 * 1000


# ============================================================================
# FEATURE ENGINEERING — COPY/PASE CHINH XAC TU train_model.py
# ============================================================================

def create_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tinh 8 engineered features — giong het train_model.py."""
    df = df.copy()
    df["bpm_spo2_ratio"] = df["bpm"] / (df["spo2"] + 1e-6)
    df["temp_gsr_interaction"] = df["body_temp"] * df["gsr_adc"] / 1000
    df["bpm_temp_product"] = df["bpm"] * df["body_temp"]
    df["spo2_gsr_ratio"] = df["spo2"] / (df["gsr_adc"] + 1e-6)
    df["bpm_deviation"] = abs(df["bpm"] - 75)
    df["temp_deviation"] = abs(df["body_temp"] - 36.8)
    df["gsr_deviation"] = abs(df["gsr_adc"] - 2200)
    df["physiological_stress_index"] = (
        (df["bpm"] - 75) / 75 + (df["gsr_adc"] - 2200) / 2200
    )
    return df


# ============================================================================
# TIMESTAMPS — RANDOMIZED, KHONG BLOCK 7 NGAY LIEN TIEP
# ============================================================================

def generate_random_timestamps(n: int, base_ts_ms: int, time_range_ms: int, seed: int) -> np.ndarray:
    """
    Random timestamps trong khoang time_range_ms tinh tu base_ts_ms.
    1 mau moi 6 phut, khong trung lap.
    """
    rng = np.random.default_rng(seed)
    interval = 6 * 60 * 1000  # 6 phut = 360000 ms
    max_intervals = time_range_ms // interval
    indices = rng.choice(max_intervals, size=n, replace=False)
    return base_ts_ms + indices * interval


# ============================================================================
# SENSOR NOISE — MO PHONG ESP32
# ============================================================================

def add_sensor_noise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Them noise do luong tu sensor ESP32:
    - MAX30102 SpO2: std=0.8
    - MAX30102 BPM:  std=3.0
    - MCP9808 body_temp: std=0.15°C
    - GSR ADC: std=200
    """
    df = df.copy()
    rng = np.random.default_rng(RANDOM_SEED + 1)
    n = len(df)

    df["spo2"] = np.clip(df["spo2"] + rng.normal(0, 0.8, n), 70, 100)
    df["bpm"] = np.clip(df["bpm"] + rng.normal(0, 3.0, n), 30, 220)
    df["body_temp"] = np.clip(df["body_temp"] + rng.normal(0, 0.15, n), 30, 42)
    df["gsr_adc"] = np.clip(df["gsr_adc"] + rng.normal(0, 200, n), 50, 50000)

    return df


# ============================================================================
# GENERATE FUNCTIONS — CHI PHAN BO SINH LY, STD NHO
# ============================================================================

def generate_normal(n: int, device_id: str, base_ts_ms: int, time_range_ms: int, seed: int) -> pd.DataFrame:
    """
    Normal (nghi ngoi, Parasympathetic hoat dong):
    - BPM: N(75, 7) — co y tuong 16% vuot qua 82
    - body_temp: N(36.5, 0.3) — co y tuong 4% > 37.5
    - GSR: N(2100, 300) — co y tuong 15% vuot qua 2500
    - SpO2: N(98.5, 1.0)
    """
    rng = np.random.default_rng(seed)

    bpm = rng.normal(75, 7, n)
    spo2 = rng.normal(98.5, 1.0, n)
    body_temp = rng.normal(36.5, 0.3, n)
    gsr_adc = rng.normal(2100, 300, n)

    df = pd.DataFrame({
        "device_id": device_id,
        "bpm": bpm,
        "spo2": spo2,
        "body_temp": body_temp,
        "gsr_adc": gsr_adc,
    })

    timestamps = generate_random_timestamps(n, base_ts_ms, time_range_ms, seed + 10)
    df["timestamp"] = timestamps
    df["ingested_at"] = pd.to_datetime(timestamps, unit="ms")

    return df


def generate_stress(n: int, device_id: str, base_ts_ms: int, time_range_ms: int, seed: int) -> pd.DataFrame:
    """
    Stress (Fight-or-Flight, Sympathetic hoat dong):
    - BPM: N(105, 14) — overlap voi Normal, 22% nam trong [75, 89]
    - body_temp: N(36.8, 0.4) — overlap voi Normal
    - GSR: N(3500, 600) — overlap voi Normal, ~20% < 2500
    - SpO2: N(98, 1.2)
    """
    rng = np.random.default_rng(seed)

    bpm = rng.normal(105, 14, n)
    spo2 = rng.normal(98, 1.2, n)
    body_temp = rng.normal(36.8, 0.4, n)
    gsr_adc = rng.normal(3500, 600, n)

    df = pd.DataFrame({
        "device_id": device_id,
        "bpm": bpm,
        "spo2": spo2,
        "body_temp": body_temp,
        "gsr_adc": gsr_adc,
    })

    timestamps = generate_random_timestamps(n, base_ts_ms, time_range_ms, seed + 20)
    df["timestamp"] = timestamps
    df["ingested_at"] = pd.to_datetime(timestamps, unit="ms")

    return df


def generate_fever(n: int, device_id: str, base_ts_ms: int, time_range_ms: int, seed: int) -> pd.DataFrame:
    """
    Fever (phan ung mien dich, set-point nao tang):
    - body_temp: N(38.5, 0.8) — co 10% y tuong < 37.5 (sot nhe)
    - base_bpm = N(80, 8) — cao hon 5 BPM vi than kinh giao cam khi sot
    - BPM = base_bpm + (body_temp - 36.8) * 12 theo Q10
    - SpO2: N(97, 1.5)
    - GSR: N(2800, 500) — overlap voi Stress, ~20% < 2500
    """
    rng = np.random.default_rng(seed)

    body_temp = rng.normal(38.5, 0.8, n)
    base_bpm = rng.normal(80, 8, n)
    q10_bpm = base_bpm + (body_temp - 36.8) * 12
    bpm = q10_bpm + rng.normal(0, 5, n)
    bpm = np.clip(bpm, 75, 135)  # clip de tranh spike nhan tao tai 85

    spo2 = rng.normal(97, 1.5, n)
    gsr_adc = rng.normal(2800, 500, n)

    df = pd.DataFrame({
        "device_id": device_id,
        "bpm": bpm,
        "spo2": spo2,
        "body_temp": body_temp,
        "gsr_adc": gsr_adc,
    })

    timestamps = generate_random_timestamps(n, base_ts_ms, time_range_ms, seed + 30)
    df["timestamp"] = timestamps
    df["ingested_at"] = pd.to_datetime(timestamps, unit="ms")

    return df


# ============================================================================
# INSERT TO MONGODB
# ============================================================================

def build_docs(df: pd.DataFrame, intended_label: str) -> list[dict]:
    """
    Build MongoDB documents from DataFrame.
    Chi ghi raw sensor data + metadata. auto_label.py se fill label/confidence.
    """
    records = df.to_dict(orient="records")
    docs = []
    for r in records:
        docs.append({
            "device_id": r["device_id"],
            "timestamp": int(r["timestamp"]),
            "bpm": round(float(r["bpm"]), 2),
            "spo2": round(float(r["spo2"]), 1),
            "body_temp": round(float(r["body_temp"]), 2),
            "gsr_adc": round(float(r["gsr_adc"]), 1),
            # Engineered features
            "bpm_spo2_ratio": round(float(r["bpm_spo2_ratio"]), 6),
            "temp_gsr_interaction": round(float(r["temp_gsr_interaction"]), 4),
            "bpm_temp_product": round(float(r["bpm_temp_product"]), 4),
            "spo2_gsr_ratio": round(float(r["spo2_gsr_ratio"]), 6),
            "bpm_deviation": round(float(r["bpm_deviation"]), 4),
            "temp_deviation": round(float(r["temp_deviation"]), 4),
            "gsr_deviation": round(float(r["gsr_deviation"]), 4),
            "physiological_stress_index": round(float(r["physiological_stress_index"]), 6),
            # ML fields — left null for auto_label.py to fill
            "predicted_label": None,
            "confidence": None,
            # Metadata
            "ingested_at": r["ingested_at"],
            "label_source": "synthetic",
            "intended_label": intended_label,
            "invalid_reading": False,
        })
    return docs


def insert_many(collection, docs: list[dict], chunk_size: int = 500):
    """Insert in chunks to avoid MongoDB size limits."""
    for i in range(0, len(docs), chunk_size):
        chunk = docs[i:i + chunk_size]
        try:
            result = collection.insert_many(chunk, ordered=False)
            print(f"  Inserted {len(result.inserted_ids)} docs (chunk {i // chunk_size + 1})")
        except Exception as e:
            print(f"  [WARN] Chunk {i // chunk_size + 1} partial failure: {e}")


# ============================================================================
# STATISTICS
# ============================================================================

def print_stats(df: pd.DataFrame, intended_label: str):
    """In thong ke co ban cua DataFrame sau noise nhung truoc auto-label."""
    print(f"\n  [{intended_label}] n={len(df)} — sau sensor noise:")
    for col in ["bpm", "spo2", "body_temp", "gsr_adc"]:
        vals = df[col].values
        print(f"    {col:20s}: mean={vals.mean():7.2f}  std={vals.std():7.2f}  "
              f"min={vals.min():7.2f}  max={vals.max():7.2f}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("  SYNTHETIC DATA GENERATOR — 15000 Samples")
    print("=" * 60)
    print(f"\nRandom seed: {RANDOM_SEED}")
    print(f"Device: {DEVICE_ID}")
    print(f"Timestamp range: {datetime(2026, 1, 1)} -> {datetime(2026, 1, 22)}")
    print(f"Samples per label: 5000")
    print(f"Timestamps: randomized within 21 days (1 sample / 6 min)")

    # Ket noi MongoDB
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print(f"\nKet noi: {MONGO_URI}/{MONGO_DB}")

    db = client[MONGO_DB]
    col = db[COLLECTION_NAME]

    # Kiem tra so luong hien tai
    existing_count = col.count_documents({})
    print(f"Tong so mau hien tai trong MongoDB: {existing_count}")

    total_new = 0

    # Sinh Normal
    print("\n--- Sinh Normal ---")
    df_normal = generate_normal(5000, DEVICE_ID, BASE_TS_MS, TIME_RANGE_MS, seed=42)
    df_normal = add_sensor_noise(df_normal)
    df_normal = create_engineered_features(df_normal)
    print_stats(df_normal, "Normal")
    docs_normal = build_docs(df_normal, "Normal")
    insert_many(col, docs_normal)
    total_new += len(docs_normal)

    # Sinh Stress
    print("\n--- Sinh Stress ---")
    df_stress = generate_stress(5000, DEVICE_ID, BASE_TS_MS, TIME_RANGE_MS, seed=142)
    df_stress = add_sensor_noise(df_stress)
    df_stress = create_engineered_features(df_stress)
    print_stats(df_stress, "Stress")
    docs_stress = build_docs(df_stress, "Stress")
    insert_many(col, docs_stress)
    total_new += len(docs_stress)

    # Sinh Fever
    print("\n--- Sinh Fever ---")
    df_fever = generate_fever(5000, DEVICE_ID, BASE_TS_MS, TIME_RANGE_MS, seed=242)
    df_fever = add_sensor_noise(df_fever)
    df_fever = create_engineered_features(df_fever)
    print_stats(df_fever, "Fever")
    docs_fever = build_docs(df_fever, "Fever")
    insert_many(col, docs_fever)
    total_new += len(docs_fever)

    # Tong ket
    new_total = col.count_documents({})
    print(f"\n{'=' * 60}")
    print(f"  Da insert: {total_new} mau moi")
    print(f"  Tong so mau trong MongoDB: {new_total}")
    print(f"{'=' * 60}")
    print(f"\n  [IMPORTANT] Chay tiep: python auto_label.py")
    print(f"  auto_label.py se fill predicted_label va confidence")
    print(f"  cho toan bo {new_total} mau (bao gom 15000 synthetic).")
    print(f"\n  LIMITATION: Fever = 100% synthetic.")
    print(f"  Khi co du lieu Fever thuc, uu tien retrain ML model.")

    client.close()


if __name__ == "__main__":
    main()
