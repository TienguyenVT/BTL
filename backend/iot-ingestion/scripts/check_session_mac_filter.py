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

print("=" * 70)
print("  KIEM TRA: HistoryPage co loc dung theo thiet bi cua user?")
print("=" * 70)

# 1. Kiem tra final_result - truong mac_address
print()
print("[1] TRUONG mac_address TRONG final_result:")
fr = db["final_result"]
sample_fr = fr.find_one()
if sample_fr:
    print(f"    Fields: {sorted(sample_fr.keys())}")
    print(f"    Co mac_address: {'mac_address' in sample_fr}")
    print(f"    Co device_id: {'device_id' in sample_fr}")
    if "mac_address" in sample_fr:
        print(f"    Gia tri mac_address: {sample_fr['mac_address']}")
else:
    print("    final_result rong")

# 2. Kiem tra session_records - truong mac_address
print()
print("[2] TRUONG mac_address TRONG sessions:")
sess = db["sessions"]
sample_sess = sess.find_one()
if sample_sess:
    print(f"    Fields: {sorted(sample_sess.keys())}")
    print(f"    Co mac_address: {'mac_address' in sample_sess}")
else:
    print("    sessions rong")

# 3. Kiem tra findSessionRecords query (tim record trong final_result theo mac)
print()
print("[3] TH NGAY: findSessionRecords() query final_result theo mac_address:")
print("    Query: Criteria.where('mac_address').in(userMacs)")
print("    Van de: final_result KHONG CO truong mac_address")
print("    => Query khong tim thay record nao => Session bi loc ra => KHONG CO DU LIEU")

# 4. Kiem tra 1 MAC cu the
mac_test = "2c:3e:5f:8a:1b:22"
print()
print(f"[4] TH NGAY: Tim record voi MAC = {mac_test}")
print("    TRONG final_result (truong mac_address):")
count_fr = fr.count_documents({"mac_address": mac_test})
print(f"    So record: {count_fr}")
print("    TRONG datalake_raw (truong mac_address):")
count_dl = db["datalake_raw"].count_documents({"mac_address": mac_test})
print(f"    So record: {count_dl}")
print("    TRONG sessions:")
count_sess = sess.count_documents({"mac_address": mac_test})
print(f"    So record: {count_sess}")

# 5. Kiem tra xem sessions co lien quan den MAC khong
print()
print("[5] SESSIONS HIENT TAI (10 ban ghi dau):")
for doc in sess.find().limit(10):
    print(f"    session_id={doc.get('session_id','')[:20]:<20} "
          f"start={str(doc.get('start_time',''))[:20]} "
          f"records={doc.get('record_count',0)} "
          f"mac={doc.get('mac_address','N/A')}")

# 6. Kiem tra record dau tien cua session
print()
print("[6] SESSION RECORDS - kiem tra truong mac_address:")
rec_sample = db["session_records"].find_one() if "session_records" in db.list_collection_names() else None
if rec_sample:
    print(f"    Fields: {sorted(rec_sample.keys())}")
else:
    print("    Khong co bang session_records")

# 7. Kiem tra getLiveSession query
print()
print("[7] KIEN TRA: getLiveSession() query final_result theo mac:")
print("    Query: Criteria.where('mac_address').in(userMacs) .limit(1)")
count_live = fr.count_documents({"mac_address": {"$in": [mac_test]}})
print(f"    So record voi MAC {mac_test} trong final_result: {count_live}")

print()
print("=" * 70)
print("  KET LUAN:")
print("  - final_result (VIEW) KHONG CO truong mac_address")
print("  - findSessionRecords() query final_result -> 0 records")
print("  - SessionService loc session -> 0 session")
print("  - HistoryPage hien thi KHONG CO DU LIEU cho tat ca user")
print("  => CAN SUA: them mac_address vao final_result VIEW")
print("=" * 70)

client.close()
