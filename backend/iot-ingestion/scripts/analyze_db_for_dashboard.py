# -*- coding: utf-8 -*-
"""Phan tich chi tiet database de nhan xet cho web dashboard"""
import os
from dotenv import load_dotenv
load_dotenv('.env')
from pymongo import MongoClient

client = MongoClient(os.getenv('MONGO_URI'))
db = client[os.getenv('MONGO_DB_NAME')]

print("=" * 70)
print("  PHAN TICH DATABASE CHO WEB DASHBOARD")
print("=" * 70)

# 1. Sessions
print("\n[1] Bang sessions")
sessions = db['sessions']
total_sessions = sessions.count_documents({})
print(f"  Tong: {total_sessions}")
session_samples = list(sessions.find().limit(5))
for s in session_samples:
    print(f"  - device={s.get('device_id')}, start={s.get('start_time')}, "
          f"end={s.get('end_time')}, label={s.get('label')}, records={s.get('record_count')}")

# 2. Devices
print("\n[2] Bang devices")
devices_coll = db['devices']
total_devices_coll = devices_coll.count_documents({})
print(f"  Tong: {total_devices_coll}")
for d in devices_coll.find():
    print(f"  - mac={d.get('mac_address')}, user_id={d.get('user_id')}")

# 3. Users
print("\n[3] Bang users")
users_coll = db['users']
total_users = users_coll.count_documents({})
print(f"  Tong: {total_users}")
for u in users_coll.find():
    print(f"  - name={u.get('name')}, email={u.get('email')}")

# 4. So sanh devices giua datalake_raw va devices collection
print("\n[4] Devices trong datalake_raw vs bang devices")
dl_devices = sorted(db['datalake_raw'].distinct('device_id'))
coll_devices = sorted([d['mac_address'] for d in devices_coll.find()])
print(f"  datalake_raw: {dl_devices}")
print(f"  devices collection: {coll_devices}")
missing_in_devices = [d for d in dl_devices if d not in coll_devices]
print(f"  Thieu trong bang devices: {missing_in_devices}")

# 5. Documents khong co prediction
print("\n[5] Documents khong co prediction.label")
no_pred = db['datalake_raw'].count_documents({'prediction.label': {'$exists': False}})
has_pred = db['datalake_raw'].count_documents({'prediction.label': {'$exists': True}})
print(f"  Co label: {has_pred}")
print(f"  Khong co label: {no_pred}")

# 6. Phan phoi label
print("\n[6] Phan phoi label trong final_result")
for r in db['final_result'].aggregate([{'$group': {'_id': '$label', 'count': {'$sum': 1}}}]):
    print(f"  {r['_id']}: {r['count']}")

# 7. Indexes
print("\n[7] Indexes tren datalake_raw")
for idx in db['datalake_raw'].list_indexes():
    print(f"  - {idx['name']}: {idx['key']}")

# 8. Thong ke sessions - gap giua cac phien
print("\n[8] Thong ke sessions - khoang cach giua cac phien")
all_sessions = list(sessions.find().sort('start_time', 1))
gaps = []
for i in range(1, len(all_sessions)):
    prev_end = all_sessions[i-1].get('end_time')
    curr_start = all_sessions[i].get('start_time')
    if prev_end and curr_start:
        gap = (curr_start - prev_end).total_seconds() / 60
        gaps.append(gap)
if gaps:
    print(f"  So gap: {len(gaps)}")
    print(f"  Gap trung binh: {sum(gaps)/len(gaps):.1f} phut")
    print(f"  Gap max: {max(gaps):.1f} phut")
    print(f"  Gap min: {min(gaps):.1f} phut")

# 9. Final_result vs realtime_health_data
print("\n[9] So sanh final_result vs realtime_health_data")
print(f"  final_result: {db['final_result'].count_documents({})} docs")
print(f"  realtime_health_data: {db['realtime_health_data'].count_documents({})} docs")
print(f"  training_health_data: {db['training_health_data'].count_documents({})} docs")

# 10. Profile
print("\n[10] Bang profiles")
profiles = db['profiles']
print(f"  Tong: {profiles.count_documents({})}")
for p in profiles.find().limit(5):
    print(f"  - user_id={p.get('user_id')}")

print("\n" + "=" * 70)
client.close()
