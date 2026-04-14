# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r"d:\Documents\BTL\backend\iot-ingestion")
from dotenv import load_dotenv
load_dotenv(r"d:\Documents\BTL\backend\iot-ingestion\.env")

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

mac_target = "2c:3e:5f:8a:1b:22"

print("=" * 70)
print("  MAPPING: device_id <-> mac_address TRONG datalake_raw")
print("=" * 70)

# Lay mapping tu datalake_raw
print()
print("[1] BANG MAP: mac_address <-> device_id (tu datalake_raw):")
pipeline = [
    {"$group": {"_id": "$device_id", "mac_address": {"$first": "$mac_address"}}},
    {"$sort": {"_id": 1}}
]
for r in db["datalake_raw"].aggregate(pipeline):
    print(f"    device_id={r['_id']:<25}  mac_address={r['mac_address']}")

# Kiem tra MAC target
print()
print(f"[2] MAC CAN TIM: {mac_target}")
doc = db["datalake_raw"].find_one({"mac_address": mac_target})
if doc:
    print(f"    TIM THAY trong datalake_raw!")
    print(f"    device_id: {doc['device_id']}")
    print(f"    mac_address: {doc['mac_address']}")
else:
    print("    KHONG TIM THAY trong datalake_raw")

# Kiem tra xem final_result VIEW co chua mac_address khong
print()
print("[3] KIEM TRA: final_result (view) co truong mac_address?")
fr = db["final_result"]
sample_fr = fr.find_one()
if sample_fr:
    print(f"    Fields trong final_result: {sorted(sample_fr.keys())}")
    has_mac = "mac_address" in sample_fr
    print(f"    Co mac_address: {has_mac}")
else:
    print("    final_result rong")

# Goc cua van de
print()
print("[4] TH NGAY: DeviceController tim mac_address TRONG final_result:")
print("    final_result KHONG CO truong mac_address!")
print("    => existingData == null => BAO LOI MAC Address khong ton tai trong he thong")

# Chinh xac loi o dau
print()
print("[5] VI TRI LOI (DeviceController.java dong 66-74):")
print('    Query checkFinalResult = new Query(')
print('        Criteria.where("mac_address").regex(normalizedMac, "i")')
print('    ).limit(1);')
print('    Document existingData = mongoTemplate.findOne(')
print('        checkFinalResult, Document.class, "final_result");')
print('    if (existingData == null) {')
print('        dto.message = "MAC Address khong ton tai trong he thong";')

# Chung minh rang final_result KHONG CHUA MAC nao
print()
print("[6] DEM SO LUONG MAC CO TRONG final_result vs datalake_raw:")
fr_distinct = db["final_result"].distinct("mac_address")
dl_distinct = db["datalake_raw"].distinct("mac_address")
print(f"    final_result distinct mac_address: {len(fr_distinct)} gia tri -> {fr_distinct}")
print(f"    datalake_raw  distinct mac_address: {len(dl_distinct)} gia tri -> {dl_distinct}")

print()
print("=" * 70)
client.close()
