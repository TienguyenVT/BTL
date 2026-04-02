# -*- coding: utf-8 -*-
"""Phan loai tat ca collections trong MongoDB theo chuan Data Lake / Datawarehouse."""
import os, sys
sys.path.insert(0, r"c:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]

print("=" * 70)
print("  PHAN TICH & PHAN LOAI MONGODB COLLECTIONS")
print("=" * 70)

for coll_name in db.list_collection_names():
    coll = db[coll_name]
    total = coll.count_documents({})
    sample = coll.find_one() or {}
    fields = set(sample.keys())

    n_label      = coll.count_documents({"label": {"$exists": True, "$ne": None}})
    n_pred       = coll.count_documents({"prediction.label": {"$exists": True, "$ne": None}})
    has_12feat   = "bpm_spo2_ratio" in fields
    has_raw      = "raw_payload" in fields or ("bpm" in fields and "bpm_spo2_ratio" not in fields)
    has_meta     = bool({"source", "schema_version", "ingested_at"} & fields)
    has_features = "features" in fields
    has_sensor   = "sensor" in fields

    print()
    print("=" * 70)
    print(f"  [{coll_name}]")
    print("=" * 70)
    print(f"  Tong docs:       {total}")
    print(f"  Fields ({len(fields)}): {sorted(fields)}")
    print(f"  has 12 features: {has_12feat}")
    print(f"  has raw payload: {has_raw}")
    print(f"  has metadata:    {has_meta}")
    print(f"  has features:    {has_features}")
    print(f"  has sensor:      {has_sensor}")
    print(f"  Co label:        {n_label} / {total}")
    print(f"  Co prediction:   {n_pred} / {total}")

    # Hien thi mau
    print()
    print("  MAU DOCUMENT (key = value):")
    skip_keys = {"_id"}
    for k, v in sample.items():
        if k in skip_keys:
            continue
        vstr = str(v)
        if len(vstr) > 110:
            vstr = vstr[:110] + " ..."
        print(f"    {k}: {vstr}")

    # Xac dinh chuc nang
    print()
    print("  PHAN LOAI CHUC NANG:")

    if has_raw and has_meta:
        print("    [DATA LAKE] Luu raw MQTT payload + rich metadata (vinh vien, khong TTL)")
        print("    - Muc dich: backup goc, khoi phuc, phan tich lai, audit")
    elif has_12feat and n_label > 0:
        print("    [TRAINING DATA] Co 12 features + label => dung de huan luyen ML")
        print("    - Muc dich: train_model.py doc tu day de huan luyen")
    elif has_12feat and n_pred > 0:
        print("    [DATAWAREHOUSE + DA GAN NHAN] Co 12 features + prediction")
        print("    - Muc dich: du lieu thuc da duoc xu ly + gan nhan (ket qua cuoi cung)")
    elif has_12feat:
        print("    [DATAWAREHOUSE (CHUA GAN NHAN)] Co 12 features nhung CHUA co label/prediction")
        print("    - Muc dich: luu du lieu thuc nhung chua qua ML /predict")
        print("    - Can: deploy Node-RED + chay Python ML server de co prediction")
    elif "bpm" in fields or "spo2" in fields:
        print("    [RAW DATA] Chi co sensor goc, chua qua feature engineering")
        print("    - Muc dich: can qua pipeline de tao 12 features")
    else:
        print("    [KHAC] Khong xac dinh duoc chuc nang")

print()
print("=" * 70)
print("  TOM TAT HE THONG")
print("=" * 70)
for coll_name in db.list_collection_names():
    total = db[coll_name].count_documents({})
    sample = db[coll_name].find_one() or {}
    fields = set(sample.keys())
    n_label = db[coll_name].count_documents({"label": {"$exists": True, "$ne": None}})
    n_pred  = db[coll_name].count_documents({"prediction.label": {"$exists": True, "$ne": None}})

    if "raw_payload" in fields and "schema_version" in fields:
        role = "DATA LAKE"
        status = f"{total} docs | khong TTL | {n_pred} co prediction"
    elif n_label > 0 and "bpm_spo2_ratio" in fields:
        role = "TRAINING DATA"
        status = f"{total} docs | {n_label} co label"
    elif n_pred > 0:
        role = "DATAWAREHOUSE (da gan nhan)"
        status = f"{total} docs | {n_pred} co prediction"
    elif "bpm_spo2_ratio" in fields:
        role = "DATAWAREHOUSE (chua gan nhan)"
        status = f"{total} docs | CHUA co prediction"
    elif "bpm" in fields or "spo2" in fields:
        role = "RAW DATA"
        status = f"{total} docs | chua feature engineering"
    else:
        role = "KHAC"
        status = f"{total} docs"

    print(f"  {coll_name}")
    print(f"    Loai:  {role}")
    print(f"    Trang thai: {status}")

client.close()
