# -*- coding: utf-8 -*-
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["iomt_health_monitor"]
coll = db["training_health_data"]

# Step 1: Xoa cac truong co the unset binh thuong
result1 = coll.update_many({}, {"$unset": {"device_id": "", "timestamp": "", "ingested_at": ""}})
print(f"Step 1 - Da xoa device_id, timestamp, ingested_at. Documents affected: {result1.modified_count}")

# Step 2: Lay tat ca documents, xoa _id bang cach replace (xoa _id)
docs = list(coll.find({}))
print(f"Step 2 - Tim thay {len(docs)} documents")

if docs:
    for doc in docs:
        doc_id = doc.pop("_id", None)  # Loai bo _id khoi dict
        if doc_id is not None:
            coll.replace_one({"_id": doc_id}, doc)
    print(f"Step 2 - Da xu ly _id cho {len(docs)} documents")

print("Hoan tat!")
