# -*- coding: utf-8 -*-
"""
Kiem tra trang thai thuc te cua final_result:
  1. So luong documents
  2. Kieu du lieu cua timestamp vs ingested_at
  3. Phan phoi timestamp: min, max, khoang cach trung binh
  4. So sessions duoc tao neu dung timestamp (hien tai)
  5. So sessions duoc tao neu dung ingested_at (truoc day)
"""
import os
import sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

print("=" * 60)
print("  KIEM TRA final_result")
print("=" * 60)

coll = db["final_result"]
total = coll.count_documents({})
print(f"\n[0] Tong documents: {total}")

# Lay 5 mau de kiem tra kieu
print("\n[1] 5 mau dau tien (kiem tra kieu du lieu):")
samples = coll.find().limit(5)
for i, doc in enumerate(samples):
    ts = doc.get("timestamp")
    ing = doc.get("ingested_at")
    ts_type = type(ts).__name__
    ing_type = type(ing).__name__
    print(f"  Doc {i+1}:")
    print(f"    timestamp ({ts_type}): {str(ts)[:80]}")
    print(f"    ingested_at ({ing_type}): {str(ing)[:80]}")
    print(f"    bpm={doc.get('bpm')}, label={doc.get('label')}")

# Kiem tra kieu cua 100 record dau tien
print("\n[2] Kiem tra kieu timestamp (100 records dau):")
ts_types = {}
sample100 = coll.find().limit(100)
for doc in sample100:
    ts = doc.get("timestamp")
    t = type(ts).__name__
    ts_types[t] = ts_types.get(t, 0) + 1
print("  Timestamp types: " + str(ts_types))

# Neu la String, kiem tra format
first_ts = coll.find_one({}, {"timestamp": 1})
if first_ts:
    ts_val = first_ts.get("timestamp")
    if isinstance(ts_val, str):
        print(f"\n  [WARN] timestamp la String! Format: '{ts_val[:50]}'")
        # Thu parse
        try:
            # Unix ms string
            int_val = int(ts_val)
            print(f"  Parse as int: {int_val}")
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(int_val / 1000, tz=timezone.utc)
            print(f"  As UTC datetime: {dt}")
        except:
            try:
                # ESP32 format
                from datetime import datetime
                fmt = "%Y:%m:%d - %H:%M:%S"
                dt = datetime.strptime(ts_val, fmt)
                print(f"  Parse as ESP32 format: {dt}")
            except Exception as e:
                print(f"  Cannot parse: {e}")

# Phan phoi thoi gian
print("\n[3] Phan phoi timestamp (sample 1000):")
samples1000 = list(coll.find().limit(1000))
if samples1000:
    ts_vals = []
    for doc in samples1000:
        ts = doc.get("timestamp")
        if isinstance(ts, (int, float)):
            ts_vals.append(float(ts))
    if ts_vals:
        ts_vals.sort()
        min_ts = ts_vals[0]
        max_ts = ts_vals[-1]
        gaps = [ts_vals[i+1] - ts_vals[i] for i in range(len(ts_vals)-1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        print(f"  Min timestamp: {min_ts} ({datetime.fromtimestamp(min_ts/1000, tz=timezone.utc)})")
        print(f"  Max timestamp: {max_ts} ({datetime.fromtimestamp(max_ts/1000, tz=timezone.utc)})")
        print(f"  Avg gap (ms): {avg_gap:.0f} ({avg_gap/1000:.1f}s)")
        print(f"  Max gap (ms): {max(gaps):.0f} ({max(gaps)/1000:.1f}s)")
        over_60s = [g for g in gaps if g > 60000]
        print(f"  Gaps > 60s: {len(over_60s)} / {len(gaps)}")

# Dem sessions theo timestamp
print("\n[4] Uoc tinh so sessions (gap > 60s theo timestamp):")
SESSION_GAP_MS = 60_000
sessions_from_ts = 0
cur_start = None
count = 0
for doc in coll.find().sort("timestamp", 1):
    ts = doc.get("timestamp")
    if not isinstance(ts, (int, float)):
        continue
    if cur_start is None:
        cur_start = ts
        count = 1
    elif ts - cur_start > SESSION_GAP_MS:
        sessions_from_ts += 1
        cur_start = ts
        count = 1
    else:
        count += 1
print(f"  Sessions (timestamp-based): {sessions_from_ts}")
print(f"  Avg records/session: {coll.count_documents({}) / max(sessions_from_ts, 1):.0f}")

# Dem sessions theo ingested_at
print("\n[5] Uoc tinh so sessions (gap > 60s theo ingested_at):")
sessions_from_ing = 0
cur_start = None
count = 0
for doc in coll.find().sort("ingested_at", 1):
    ing = doc.get("ingested_at")
    if ing is None:
        continue
    if isinstance(ing, datetime):
        ts = ing.timestamp() * 1000
    elif isinstance(ing, (int, float)):
        ts = float(ing)
    else:
        continue
    if cur_start is None:
        cur_start = ts
        count = 1
    elif ts - cur_start > SESSION_GAP_MS:
        sessions_from_ing += 1
        cur_start = ts
        count = 1
    else:
        count += 1
print(f"  Sessions (ingested_at-based): {sessions_from_ing}")
print(f"  Avg records/session: {coll.count_documents({}) / max(sessions_from_ing, 1):.0f}")

# So sanh
print("\n" + "=" * 60)
print(f"  final_result: {total} records")
print(f"  Sessions theo timestamp:   {sessions_from_ts} (avg {total/max(sessions_from_ts,1):.0f} records/session)")
print(f"  Sessions theo ingested_at: {sessions_from_ing} (avg {total/max(sessions_from_ing,1):.0f} records/session)")
print("=" * 60)

client.close()
