# -*- coding: utf-8 -*-
"""Simulate the FIXED Java backend logic in Python"""
import os, sys, json
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
fr = db["final_result"]

print("=" * 70)
print("  SIMULATION: Fixed Backend Logic")
print("=" * 70)

# === H1 FIX: /latest — query ALL, sort by ingested_at DESC, limit 1 ===
print("\n[H1 FIX] /latest — no device filter, sort by ingested_at DESC, limit 1")
query = fr.find().sort("ingested_at", -1).limit(1)
docs = list(query)
print(f"  Found: {len(docs)}")
if docs:
    doc = docs[0]
    print(f"  ingested_at: {doc.get('ingested_at')}")
    print(f"  bpm: {doc.get('bpm')} | spo2: {doc.get('spo2')} | body_temp: {doc.get('body_temp')}")
    print(f"  label: {doc.get('label')}")
    # Convert ingested_at to epoch ms (what Java does)
    ia = doc.get("ingested_at")
    if ia:
        if hasattr(ia, 'timestamp'):
            epoch_ms = int(ia.timestamp() * 1000)
        else:
            epoch_ms = int(ia.replace(tzinfo=timezone.utc).timestamp() * 1000)
        print(f"  epoch_ms (FE will use): {epoch_ms}")
        print(f"  new Date(epoch_ms): {datetime.fromtimestamp(epoch_ms/1000, tz=timezone.utc)}")

# === H2 FIX: /history — query ALL, sort by ingested_at ASC ===
print("\n[H2 FIX] /history — no device filter, use ingested_at >= time_ago")
time_ago = datetime.now(timezone.utc) - timedelta(hours=24)
print(f"  time_ago: {time_ago}")
query2 = fr.find({"ingested_at": {"$gte": time_ago}}).sort("ingested_at", 1)
docs2 = list(query2)
print(f"  Found: {len(docs2)} docs in last 24h")

# Also try without time filter to see ALL data
print("\n[ALL DATA] final_result total:")
all_docs = list(fr.find().sort("ingested_at", 1))
print(f"  Total: {len(all_docs)}")
if all_docs:
    print(f"  Oldest: ingested_at={all_docs[0].get('ingested_at')} bpm={all_docs[0].get('bpm')}")
    print(f"  Newest: ingested_at={all_docs[-1].get('ingested_at')} bpm={all_docs[-1].get('bpm')}")

# Check: is the data within 24h?
print(f"\n  Current time: {datetime.now(timezone.utc)}")
print(f"  Data is from: {all_docs[-1].get('ingested_at') if all_docs else 'N/A'}")

client.close()
