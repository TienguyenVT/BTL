# -*- coding: utf-8 -*-
"""Xoa raw_sensor (cu) va xac nhan datalake_raw moi."""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

print("=" * 60)
print("  XOA raw_sensor (CU)")
print("=" * 60)

collections_before = db.list_collection_names()
print("\n[1] Collections BEFORE:")
for c in collections_before:
    n = db[c].count_documents({})
    print("    " + c + ": " + str(n) + " docs")

# Xoa raw_sensor
if "raw_sensor" in collections_before:
    count = db["raw_sensor"].count_documents({})
    db["raw_sensor"].drop()
    print("\n[2] Da xoa 'raw_sensor': " + str(count) + " docs")
else:
    print("\n[2] 'raw_sensor' khong ton tai, bo qua.")

collections_after = db.list_collection_names()
print("\n[3] Collections AFTER:")
for c in collections_after:
    n = db[c].count_documents({})
    print("    " + c + ": " + str(n) + " docs")

# Hien thi 1 mau datalake_raw
print("\n[4] Mau document datalake_raw (khong co _id):")
coll = db["datalake_raw"]
sample = coll.find_one()
if sample:
    for k, v in sample.items():
        if k != "_id":
            vstr = str(v)
            if len(vstr) > 80:
                vstr = vstr[:80] + " ..."
            print("    " + str(k) + ": " + vstr)

# Thong ke prediction
pred_null = coll.count_documents({"prediction": None})
pred_ok = coll.count_documents({"prediction": {"$ne": None}})
print("\n[5] Prediction stats:")
print("    Null: " + str(pred_null))
print("    Co ket qua: " + str(pred_ok))

client.close()
print("\n" + "=" * 60)
print("  HOAN TAT!")
print("=" * 60)
