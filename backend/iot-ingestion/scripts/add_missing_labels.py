# -*- coding: utf-8 -*-
"""Them label vao 2 docs con thieu trong training_health_data."""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI","mongodb://localhost:27017"))
coll = client[os.getenv("MONGO_DB_NAME","iomt_health_monitor")]["training_health_data"]

# Tim docs khong co label
missing = list(coll.find({"label": {"$exists": False}}))
print(f"Docs khong co label: {len(missing)}")
for d in missing:
    print(f"  _id={d['_id']}")
    print(f"  keys={list(d.keys())}")

# Gan label mac dinh la Normal
result = coll.update_many({"label": {"$exists": False}}, {"$set": {"label": "Normal"}})
print(f"Da them label=Normal cho {result.modified_count} docs")
client.close()
