# -*- coding: utf-8 -*-
"""Diagnostic script - check all potential causes of no data on FE"""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from datetime import datetime

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

print("=" * 70)
print("  DIAGNOSTIC: Why FE shows NO DATA")
print("=" * 70)

# Check 1: Devices collection
print("\n[CHECK 1] devices collection (user_id -> mac_address mapping)")
devices_coll = db["devices"]
all_devices = list(devices_coll.find())
print(f"  Total devices: {len(all_devices)}")
for d in all_devices:
    print(f"    user_id={d.get('user_id')} | mac_address={d.get('mac_address')} | name={d.get('name')}")

# Check 2: final_result device_ids
print("\n[CHECK 2] final_result device_id values")
fr_coll = db["final_result"]
fr_device_ids = set(d.get("device_id") for d in fr_coll.find())
print(f"  Device IDs in final_result: {fr_device_ids}")

# Check 3: timestamp format
print("\n[CHECK 3] final_result timestamp FORMAT (critical!)")
sample_ts = fr_coll.find_one()
ts_val = sample_ts.get("timestamp")
print(f"  Sample timestamp value: {repr(ts_val)}")
print(f"  Type: {type(ts_val).__name__}")
if isinstance(ts_val, str):
    print("  PROBLEM: timestamp is STRING, NOT Unix epoch!")
    print("  HealthController queries: timestamp >= Instant.now() - hours")
    print("  String comparison '2026:03:31 - 15:55:20' >= '174...' will FAIL!")
elif isinstance(ts_val, (int, float)):
    print(f"  OK: timestamp is numeric ({ts_val})")

# Check 4: ingested_at format
ingested = sample_ts.get("ingested_at")
print(f"  ingested_at: {repr(ingested)} type={type(ingested).__name__}")

# Check 5: Match analysis
print("\n[CHECK 4] Device match analysis")
dev_macs = {d.get("mac_address") for d in all_devices}
overlap = fr_device_ids & dev_macs
print(f"  final_result device_ids: {fr_device_ids}")
print(f"  devices mac_addresses: {dev_macs}")
print(f"  OVERLAP: {overlap}")
if not overlap:
    print("  ROOT CAUSE: NO device in 'devices' collection matches final_result!")
    print("  findDefaultDeviceId() returns null -> HealthController returns null!")

# Check 6: Manual query simulating what Java does
print("\n[CHECK 5] Simulating Java query with mac_address='esp32_iot_health_01'")
from bson import Document
from pymongo import DESCENDING
from datetime import timedelta
time_ago = datetime.now() - timedelta(hours=24)
print(f"  Time threshold: {time_ago}")

# Find docs with this device_id
docs_for_device = list(fr_coll.find({"device_id": "esp32_iot_health_01"}).sort("ingested_at", DESCENDING).limit(3))
print(f"  Docs found for device_id='esp32_iot_health_01': {len(docs_for_device)}")
for d in docs_for_device:
    print(f"    ingested_at={d.get('ingested_at')} bpm={d.get('bpm')} label={d.get('label')}")

print("\n[CHECK 6] ingested_at field type across docs")
types_seen = set()
samples_by_type = {}
for d in fr_coll.find().limit(10):
    t = type(d.get("ingested_at")).__name__
    types_seen.add(t)
    if t not in samples_by_type:
        samples_by_type[t] = d.get("ingested_at")
print(f"  Types seen: {types_seen}")
for t, v in samples_by_type.items():
    print(f"    {t}: {repr(v)}")

# Check 7: What if we query by ingested_at (datetime)?
print("\n[CHECK 7] Alternative query using ingested_at (datetime)")
docs_by_ingested = list(fr_coll.find({
    "device_id": "esp32_iot_health_01",
    "ingested_at": {"$gte": time_ago}
}).sort("ingested_at", DESCENDING).limit(3))
print(f"  Found by ingested_at >= {time_ago}: {len(docs_by_ingested)}")

client.close()
print("\n" + "=" * 70)
