from pymongo import MongoClient
import os
from dotenv import load_dotenv
import hashlib
import datetime

load_dotenv(r"c:\Documents\BTL\backend\iot-ingestion\.env")
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB_NAME", "iomt_health_monitor")]

TS_PARSE_FMT = "%Y:%m:%d - %H:%M:%S"
VN_OFFSET = datetime.timezone(datetime.timedelta(hours=7))

def derive_session_id(first_record):
    ts = first_record.get("timestamp")
    device_id = first_record.get("device_id")
    key = (ts if ts else "") + "|" + (device_id if device_id else "")
    return str(hashlib.md5(key.encode()).hexdigest())

# Read all final_result
docs = list(db["final_result"].find().sort("ingested_at", 1))
print(f"Total records: {len(docs)}")

# Detect sessions (gap > 60s)
SESSION_GAP_MS = 60 * 1000
groups = []
current_group = None

for doc in docs:
    ingested = doc["ingested_at"]
    ts_str = doc["timestamp"]

    # Parse timestamp string "yyyy:MM:dd - HH:mm:ss" as UTC+7
    ldt = datetime.datetime.strptime(ts_str, TS_PARSE_FMT)
    ts_utc7 = ldt.replace(tzinfo=VN_OFFSET)
    ts_ms = int(ts_utc7.timestamp() * 1000)

    if current_group is None:
        sid = derive_session_id(doc)
        current_group = {"id": sid, "start_ts": ts_utc7, "end_ts": ts_utc7, "docs": [doc]}
    elif abs(ts_ms - int(current_group["end_ts"].timestamp() * 1000)) > SESSION_GAP_MS:
        groups.append(current_group)
        sid = derive_session_id(doc)
        current_group = {"id": sid, "start_ts": ts_utc7, "end_ts": ts_utc7, "docs": [doc]}
    else:
        current_group["docs"].append(doc)
        if ts_utc7 > current_group["end_ts"]:
            current_group["end_ts"] = ts_utc7

if current_group:
    groups.append(current_group)

print(f"Detected sessions: {len(groups)}")
print()
for g in groups:
    start_str = g["start_ts"].strftime("%Y-%m-%d %H:%M:%S")
    end_str = g["end_ts"].strftime("%Y:%m:%d - %H:%M:%S")
    print(f"  session_id: {g['id']}")
    print(f"  start:      {start_str} UTC+7  ({int(g['start_ts'].timestamp() * 1000)} ms)")
    print(f"  end ts str: {end_str}")
    print(f"  records:    {len(g['docs'])}")
    # Verify: query by timestamp string
    start_ts_str = g["start_ts"].strftime(TS_PARSE_FMT)
    end_ts_str = g["end_ts"].strftime(TS_PARSE_FMT)
    found = list(db["final_result"].find({
        "timestamp": {"$gte": start_ts_str, "$lte": end_ts_str}
    }).sort("timestamp", 1))
    match = "OK" if len(found) == len(g["docs"]) else "MISMATCH"
    print(f"  query by ts string: found={len(found)} expected={len(g['docs'])} {match}")
    print()

print("=== Frontend IDs check ===")
frontend_ids = [
    "cbc86d92-48ec-4d7e-889a-0cb4fa7961a6",  # from latest error
    "2e253a00-7e52-4012-a74e-303ffc208cf9",   # from earlier error
    "2135ff71-e7e3-45b6-887a-8cd7a6e64062",   # from earliest error
]
current_ids = [g["id"] for g in groups]
for fid in frontend_ids:
    if fid in current_ids:
        print(f"  {fid} -> FOUND in DB")
    else:
        print(f"  {fid} -> NOT FOUND (stale UUID)")
