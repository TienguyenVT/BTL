# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

# 1. Check final_result timestamp types
print("=== final_result timestamp types ===")
coll = db["final_result"]
docs = coll.find().sort("ingested_at", -1).limit(5)
for d in docs:
    ts = d.get("timestamp")
    print(f"  ts={repr(ts)} type={type(ts).__name__}")

print()

# 2. Check devices collection
print("=== devices collection ===")
devices = db["devices"]
dev_list = list(devices.find())
print(f"  Total: {len(dev_list)}")
for dev in dev_list:
    print(f"  user_id={dev.get('user_id')} mac={dev.get('mac_address')} name={dev.get('name')}")

print()

# 3. Check device_ids in final_result vs devices
fr_device_ids = set()
for d in coll.find():
    fr_device_ids.add(d.get("device_id"))
print(f"device_ids in final_result: {fr_device_ids}")

dev_mac_ids = set(d.get("mac_address") for d in dev_list)
print(f"mac_addresses in devices:   {dev_mac_ids}")

print()
print("=== OVERLAP ===")
overlap = fr_device_ids & dev_mac_ids
print(f"Overlap (device_id == mac_address): {overlap}")

print()
print("=== User profiles ===")
users = db["users"]
for u in users.find():
    print(f"  id={u.get('_id')} email={u.get('email')} name={u.get('name')}")

client.close()
