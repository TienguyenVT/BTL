from pymongo import MongoClient
import os
from dotenv import load_dotenv
import datetime

load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB_NAME", "iomt_health_monitor")]

print("Verify fix: end_time + 999ms")
print()
for s in db["sessions"].find().sort("start_time", 1):
    st = s["start_time"]
    en = s["end_time"]
    en_fixed = en + datetime.timedelta(microseconds=999000)
    count = db["final_result"].count_documents({"ingested_at": {"$gte": st, "$lt": en_fixed}})
    print(f"Session {str(st)[:19]} -> {str(en)[:19]}")
    print(f"  end+999ms: found {count} records (expected {s['record_count']})")
