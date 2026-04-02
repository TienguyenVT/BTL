# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
coll = db["final_result"]

print("=== final_result LABEL STATS ===")
for r in coll.aggregate([{"$group": {"_id": "$label", "count": {"$sum": 1}}}]):
    print("  " + str(r["_id"]) + ": " + str(r["count"]))

print()
print("=== 5 MAU DOCS GAN NHAT ===")
for doc in coll.find().sort("ingested_at", -1).limit(5):
    ts   = doc.get("timestamp", "")
    lbl  = doc.get("label", "")
    conf = doc.get("confidence", "")
    bpm  = doc.get("bpm", "")
    sp2  = doc.get("spo2", "")
    bt   = doc.get("body_temp", "")
    gsr  = doc.get("gsr_adc", "")
    print("  ts=" + str(ts) + "  bpm=" + str(bpm) + "  spo2=" + str(sp2) +
          "  body_temp=" + str(bt) + "  gsr=" + str(gsr) +
          "  label=" + str(lbl) + "  conf=" + str(conf))

print()
print("=== HE THONG 4 BANG ===")
for coll_name in db.list_collection_names():
    c = db[coll_name]
    total = c.count_documents({})
    s = c.find_one() or {}
    fields = sorted([k for k in s.keys() if k != "_id"])

    if coll_name == "final_result":
        role = "KET QUA CUOI CUNG (DA XU LY + GAN NHAN)"
    elif coll_name == "datalake_raw":
        role = "DATA LAKE (raw payload + metadata, vinh vien)"
    elif coll_name == "realtime_health_data":
        role = "DATAWAREHOUSE (12 features, chua gan nhan)"
    elif coll_name == "training_health_data":
        role = "TRAINING DATA (co label, dung huan luyen ML)"
    else:
        role = "KHAC"

    print()
    print("  [" + coll_name + "]  " + role)
    print("    Docs: " + str(total))
    print("    Fields: " + str(fields))

client.close()
