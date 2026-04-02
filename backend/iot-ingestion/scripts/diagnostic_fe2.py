# -*- coding: utf-8 -*-
"""Full diagnostic for FE no-data issue"""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
fr = db["final_result"]

# Check 5: Simulating Java query with mac_address='esp32_iot_health_01'
print("[CHECK 5] Simulating Java query by device_id + timestamp")
time_ago = datetime.now() - timedelta(hours=24)
print(f"  Time threshold: {time_ago}")

docs_for_device = list(fr.find({"device_id": "esp32_iot_health_01"}).sort("ingested_at", -1).limit(3))
print(f"  Docs found for device_id='esp32_iot_health_01': {len(docs_for_device)}")
for d in docs_for_device:
    print(f"    ingested_at={d.get('ingested_at')} bpm={d.get('bpm')} label={d.get('label')}")

# Check 6: ingested_at field type across docs
print("\n[CHECK 6] ingested_at field type")
types_seen = set()
for d in fr.find().limit(10):
    t = type(d.get("ingested_at")).__name__
    types_seen.add(t)
print(f"  Types seen: {types_seen}")

# Check 7: Query by ingested_at (datetime) instead of timestamp (string)
print("\n[CHECK 7] Query using ingested_at >= time_ago")
docs_by_ingested = list(fr.find({
    "device_id": "esp32_iot_health_01",
    "ingested_at": {"$gte": time_ago}
}).sort("ingested_at", -1).limit(3))
print(f"  Found: {len(docs_by_ingested)}")

# Check 8: What timestamps are in final_result?
print("\n[CHECK 8] All distinct timestamp values (sample)")
ts_samples = [d.get("timestamp") for d in fr.find().limit(3)]
for t in ts_samples:
    print(f"  {repr(t)} ({type(t).__name__})")

# Check 9: Query by timestamp string range (Java does this!)
import calendar
now_epoch = calendar.timegm(datetime.now().timetuple()) * 1000
time_ago_epoch = calendar.timegm((datetime.now() - timedelta(hours=24)).timetuple()) * 1000
print(f"\n[CHECK 9] Java query by timestamp (epoch): timestamp >= {time_ago_epoch}")
print(f"  final_result has string timestamps: '{ts_samples[0]}'")
print(f"  Comparing string '2026:03:31 - 15:55:20' >= numeric epoch {time_ago_epoch}")
try:
    result = "2026:03:31 - 15:55:20" >= time_ago_epoch
    print(f"  Result: {result} (THIS IS THE BUG)")
except TypeError as e:
    print(f"  TypeError: {e} (THIS IS ALSO THE BUG)")

client.close()
