# -*- coding: utf-8 -*-
"""Xoa truong mode khoi training_health_data (neu con ton tai)."""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI","mongodb://localhost:27017"))
coll = client[os.getenv("MONGO_DB_NAME","iomt_health_monitor")]["training_health_data"]

result = coll.update_many({"mode": {"$exists": True}}, {"$unset": {"mode": ""}})
print(f"Da xoa mode khoi training: {result.modified_count} docs")
client.close()
