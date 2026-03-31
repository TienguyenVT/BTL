# -*- coding: utf-8 -*-
"""
Truy vấn collection realtime_health_data trong MongoDB.
"""

import sys
sys.path.insert(0, "C:/Documents/BTL/backend/iot-ingestion")

from dotenv import load_dotenv
load_dotenv("C:/Documents/BTL/backend/iot-ingestion/.env")

from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")
COLLECTION_NAME = "realtime_health_data"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print(f"Ket noi thanh cong den MongoDB: {MONGO_URI}")
except Exception as e:
    print(f"Loi ket noi MongoDB: {e}")
    sys.exit(1)

db = client[MONGO_DB]
col = db[COLLECTION_NAME]

total_count = col.count_documents({})
print(f"\nTong so mau du lieu trong collection '{COLLECTION_NAME}': {total_count}")

if total_count > 0:
    print(f"\n--- Mot so mau dau tien ---")
    for doc in col.find().sort("timestamp", -1).limit(3):
        doc.pop("_id", None)
        print(doc)

    print(f"\n--- Xem cau truc 1 mau ---")
    sample = col.find_one()
    if sample:
        print(f"Cac truong co trong document:")
        for key in sample.keys():
            print(f"  - {key}")
else:
    print("Collection trong hoac chua co du lieu.")

client.close()
print("\nDa dong ket noi MongoDB.")