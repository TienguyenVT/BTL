from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB_NAME", "iomt_health_monitor")]

frontend_id = "2e253a00-7e52-4012-a74e-303ffc208cf9"
exists = db["sessions"].count_documents({"session_id": frontend_id})
print("Frontend session ID: " + frontend_id)
print("Exists in sessions: " + str(exists))
print()

print("Current sessions in DB:")
for s in db["sessions"].find().sort("start_time", 1):
    marker = " <-- FRONTEND REQUESTING" if s["session_id"] == frontend_id else ""
    print("  " + s["session_id"] + " | " + str(s["start_time"])[:19] + " | " + str(s["record_count"]) + " records" + marker)
