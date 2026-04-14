# -*- coding: utf-8 -*-
"""
Xoa toan bo sessions trong MongoDB.
Chay sau khi da fix SESSION_GAP_MS va restart backend.
Backend se tu dong rebuild sessions moi tu final_result.
"""
import os
import sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

print("=" * 60)
print("  XOA SESSIONS COLLECTION")
print("=" * 60)

coll = "sessions"
if coll in db.list_collection_names():
    count = db[coll].count_documents({})
    db[coll].drop()
    print(f"Da xoa '{coll}' ({count} documents).")
else:
    print(f"Collection '{coll}' khong ton tai, khong can xoa.")

client.close()
print("Xong!")
