from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB_NAME", "iomt_health_monitor")]

# Lay session ID tu frontend
frontend_id = "cbc86d92-48ec-4d7e-889a-0cb4fa7961a6"

# Kiem tra trong sessions
sess = db["sessions"].find_one({"session_id": frontend_id})
print("=== Session in DB ===")
if sess:
    print("  FOUND")
    print("  session_id: " + str(sess.get("session_id")))
    print("  start_time: " + str(sess.get("start_time")))
    print("  end_time:   " + str(sess.get("end_time")))
    print("  record_count: " + str(sess.get("record_count")))
else:
    print("  NOT FOUND in sessions collection")

# Kiem tra coi co trong collection nao khac khong
print()
print("=== Searching all collections ===")
for col_name in db.list_collection_names():
    if col_name.startswith("system"):
        continue
    count = db[col_name].count_documents({"session_id": frontend_id})
    if count > 0:
        print(f"  Found {count} docs in '{col_name}'")
        doc = db[col_name].find_one({"session_id": frontend_id})
        for k, v in sorted(doc.items()):
            print(f"    {k}: {repr(v)[:100]}")

# Neu khong co trong sessions, xem session nao moi nhat
print()
print("=== All sessions ===")
for s in db["sessions"].find().sort("start_time", -1):
    print("  " + s["session_id"] + " | " + str(s["start_time"])[:30] + " | " + str(s["record_count"]) + " records")

# Kiem tra final_result collection
print()
print("=== final_result sample (first 3) ===")
for d in db["final_result"].find().sort("ingested_at", 1).limit(3):
    print("  ingested_at: " + str(d.get("ingested_at")))
    print("  timestamp:   " + str(d.get("timestamp")))
    for k, v in sorted(d.items()):
        if k not in ("_id", "ingested_at", "timestamp"):
            print(f"  {k}: {repr(v)[:80]}")
    print()
