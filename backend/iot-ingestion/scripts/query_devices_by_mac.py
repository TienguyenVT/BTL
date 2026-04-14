# -*- coding: utf-8 -*-
"""
Truy van so luong thiet bi trong bang final_result (theo MAC address / device_id)
"""
import os
import sys
sys.path.insert(0, r"d:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"d:\Documents\BTL\backend\iot-ingestion\.env")

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

coll = db["final_result"]

print("=" * 60)
print("  Kiem tra so thiet bi trong bang final_result")
print("=" * 60)

# Tong so documents
total_docs = coll.count_documents({})
print(f"\n[0] Tong so documents trong final_result: {total_docs}")

# Dem so device_id (MAC address) unique
unique_devices = coll.distinct("device_id")
num_devices = len(unique_devices)

print(f"\n[1] So luong thiet bi (MAC address unique): {num_devices}")

# Hien thi chi tiet tung thiet bi
print(f"\n[2] Chi tiet tung thiet bi:")
print("-" * 60)
for i, mac in enumerate(sorted(unique_devices), 1):
    count = coll.count_documents({"device_id": mac})
    print(f"  {i}. {mac:<20} | {count} records")
print("-" * 60)
print(f"  Tong cong: {num_devices} thiet bi")

# Thong ke them: thoi gian dau tien va cuoi cung cho moi thiet bi
print(f"\n[3] Thoi gian ghi nhan cuoi cung cua moi thiet bi:")
print("-" * 60)

for mac in sorted(unique_devices):
    # Tim record cuoi cung (timestamp lon nhat)
    latest = coll.find_one(
        {"device_id": mac},
        sort=[("timestamp", -1)]
    )
    earliest = coll.find_one(
        {"device_id": mac},
        sort=[("timestamp", 1)]
    )

    if latest and earliest:
        from datetime import datetime, timezone

        # Parse timestamp (co the la string hoac int)
        latest_ts_raw = latest["timestamp"]
        earliest_ts_raw = earliest["timestamp"]

        try:
            latest_ts_val = int(latest_ts_raw)
            earliest_ts_val = int(earliest_ts_raw)
            latest_dt = datetime.fromtimestamp(latest_ts_val / 1000, tz=timezone.utc)
            earliest_dt = datetime.fromtimestamp(earliest_ts_val / 1000, tz=timezone.utc)
        except (TypeError, ValueError):
            # Neu khong phai int, hien thi nguyen van
            latest_dt = latest_ts_raw
            earliest_dt = earliest_ts_raw

        print(f"  {mac}: first={earliest_dt}, last={latest_dt}")

print("=" * 60)

client.close()
