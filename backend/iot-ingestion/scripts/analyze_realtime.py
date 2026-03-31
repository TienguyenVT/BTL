# -*- coding: utf-8 -*-
"""
Phan tich phan bo du lieu trong collection realtime_health_data (MongoDB).
Dung de lay cac chi so P75/P85 cua GSR_ADC lam nguong Stress,
va kiem tra phan bo cac sensor fields truoc khi gán nhan.

Su dung: python analyze_realtime.py
"""

import sys
import os
sys.path.insert(0, "C:/Documents/BTL/backend/iot-ingestion")

from dotenv import load_dotenv
load_dotenv("C:/Documents/BTL/backend/iot-ingestion/.env")

from pymongo import MongoClient, DESCENDING
import numpy as np

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")
COLLECTION_NAME = "realtime_health_data"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
client.admin.command("ping")
print(f"Da ket noi MongoDB: {MONGO_URI}")

db = client[MONGO_DB]
col = db[COLLECTION_NAME]

# Lay tat ca docs
docs = list(col.find())
total = len(docs)
print(f"\nTong so mau: {total}")

# Tach fields
bpm_list = [d.get("bpm", 0) for d in docs]
spo2_list = [d.get("spo2", 0) for d in docs]
temp_list = [d.get("body_temp", 0) for d in docs]
gsr_list = [d.get("gsr_adc", 0) for d in docs]
mode_list = [d.get("mode", None) for d in docs]

arr_bpm = np.array(bpm_list, dtype=float)
arr_spo2 = np.array(spo2_list, dtype=float)
arr_temp = np.array(temp_list, dtype=float)
arr_gsr = np.array(gsr_list, dtype=float)

def stats(arr, name):
    valid = arr[arr > 0]
    print(f"\n--- {name} ---")
    print(f"  Total:      {len(arr)}")
    print(f"  Invalid(0): {np.sum(arr == 0)}")
    if len(valid) > 0:
        print(f"  Valid range: {valid.min():.2f} - {valid.max():.2f}")
        print(f"  Mean:       {valid.mean():.2f}")
        print(f"  Std:        {valid.std():.2f}")
        print(f"  P25:        {np.percentile(valid, 25):.2f}")
        print(f"  P50:        {np.percentile(valid, 50):.2f}")
        print(f"  P75:        {np.percentile(valid, 75):.2f}")
        print(f"  P85:        {np.percentile(valid, 85):.2f}")
        print(f"  P90:        {np.percentile(valid, 90):.2f}")
        print(f"  P95:        {np.percentile(valid, 95):.2f}")
    return valid

stats(arr_bpm, "BPM")
stats(arr_spo2, "SpO2")
stats(arr_temp, "Body_Temp")
gsr_valid = stats(arr_gsr, "GSR_ADC")

# GSR threshold recommendation
gsr_p75 = np.percentile(gsr_valid, 75)
gsr_p85 = np.percentile(gsr_valid, 85)
gsr_threshold = max(gsr_p75, 2500)
print(f"\n>>> GSR Threshold de recommend: max(P75={gsr_p75:.0f}, 2500) = {gsr_threshold:.0f}")
print(f">>> GSR P85 = {gsr_p85:.0f}")

# Mode distribution
from collections import Counter
mode_counts = Counter(mode_list)
print(f"\n--- Mode distribution ---")
for k, v in sorted(mode_counts.items(), key=lambda x: str(x[0])):
    print(f"  mode={k}: {v}")

# Extreme samples
print(f"\n--- Extreme samples ---")
valid_docs = [d for d in docs if d.get("bpm", 0) > 0 and d.get("spo2", 0) > 0 and d.get("body_temp", 0) > 0]

if valid_docs:
    # Highest BPM
    highest_bpm = max(valid_docs, key=lambda d: d.get("bpm", 0))
    print(f"  Highest BPM:  {highest_bpm.get('bpm')} | temp={highest_bpm.get('body_temp')} | gsr={highest_bpm.get('gsr_adc')} | time={highest_bpm.get('ingested_at')}")
    # Lowest SpO2
    lowest_spo2 = min(valid_docs, key=lambda d: d.get("spo2", 0))
    print(f"  Lowest SpO2:  {lowest_spo2.get('spo2')} | bpm={lowest_spo2.get('bpm')} | temp={lowest_spo2.get('body_temp')} | time={lowest_spo2.get('ingested_at')}")
    # Highest Temp
    highest_temp = max(valid_docs, key=lambda d: d.get("body_temp", 0))
    print(f"  Highest Temp: {highest_temp.get('body_temp')} | bpm={highest_temp.get('bpm')} | gsr={highest_temp.get('gsr_adc')} | time={highest_temp.get('ingested_at')}")
    # Highest GSR
    highest_gsr = max(valid_docs, key=lambda d: d.get("gsr_adc", 0))
    print(f"  Highest GSR:  {highest_gsr.get('gsr_adc')} | bpm={highest_gsr.get('bpm')} | temp={highest_gsr.get('body_temp')} | time={highest_gsr.get('ingested_at')}")

# Time range
ingested = [d.get("ingested_at") for d in docs if d.get("ingested_at")]
if ingested:
    print(f"\n--- Time range ---")
    print(f"  Earliest: {min(ingested)}")
    print(f"  Latest:   {max(ingested)}")

client.close()
print("\n[Done] Phan tich hoan tat.")
