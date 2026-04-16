# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017')
db = client['iomt_health_monitor']

print('=== REALTIME_HEALTH_DATA (Node-RED Output 1) ===')
rt_count = db['realtime_health_data'].count_documents({})
print('  Count: %d' % rt_count)
if rt_count > 0:
    latest = db['realtime_health_data'].find_one(sort=[('_id', -1)])
    print('  Latest fields: %s' % sorted([k for k in latest.keys() if k != '_id']))
    print('  Has predicted_label: %s' % ('predicted_label' in latest))

print()
print('=== SESSIONS ===')
sess_count = db['sessions'].count_documents({})
print('  sessions count: %d' % sess_count)
if sess_count > 0:
    latest_sess = db['sessions'].find_one(sort=[('start_time', -1)])
    print('  Latest session: start=%s, end=%s, active=%s, records=%s' % (
        latest_sess.get('start_time'), latest_sess.get('end_time'), 
        latest_sess.get('active'), latest_sess.get('record_count')))

print()
print('=== MAC_ADDRESS check ===')
# Check mac_address in final_result view
sample_fr = db['final_result'].find_one()
if sample_fr:
    mac = sample_fr.get('mac_address')
    print('  final_result mac_address: "%s" (type: %s)' % (mac, type(mac).__name__))

# Check mac_address in datalake_raw
raw_sample = db['datalake_raw'].find_one()
if raw_sample:
    raw_mac = raw_sample.get('mac_address')
    raw_payload_mac = None
    if raw_sample.get('raw_payload'):
        raw_payload_mac = raw_sample['raw_payload'].get('mac_address')
    print('  datalake_raw mac_address (top): "%s"' % raw_mac)
    print('  datalake_raw.raw_payload.mac_address: "%s"' % raw_payload_mac)

print()
print('=== DATA BY DATE ===')
# Check data distributed by date
pipeline_dates = [
    {"$group": {
        "_id": {
            "$dateToString": {"format": "%Y-%m-%d", "date": "$ingested_at"}
        },
        "count": {"$sum": 1},
        "min_ts": {"$min": "$ingested_at"},
        "max_ts": {"$max": "$ingested_at"}
    }},
    {"$sort": {"_id": -1}},
    {"$limit": 10}
]
for r in db['datalake_raw'].aggregate(pipeline_dates):
    print('  %s: %d records (from %s to %s)' % (r['_id'], r['count'], r['min_ts'], r['max_ts']))

print()
print('=== DATA BY HOUR TODAY ===')
today_start = datetime(2026, 4, 16, 0, 0, 0)
pipeline_hours = [
    {"$match": {"ingested_at": {"$gte": today_start}}},
    {"$group": {
        "_id": {
            "$dateToString": {"format": "%Y-%m-%d %H:00", "date": "$ingested_at"}
        },
        "count": {"$sum": 1}
    }},
    {"$sort": {"_id": 1}}
]
for r in db['datalake_raw'].aggregate(pipeline_hours):
    print('  %s -> %d records' % (r['_id'], r['count']))

print()
print('=== ALL COLLECTIONS ===')
for c in db.list_collection_names():
    try:
        cnt = db[c].count_documents({})
        ctype = 'view' if any(ci['name'] == c and ci.get('type') == 'view' for ci in db.list_collections()) else 'collection'
        print('  %s (%s): %d' % (c, ctype, cnt))
    except Exception as e:
        print('  %s: ERROR %s' % (c, e))

print()
print('=== VIEW _id ISSUE CHECK ===')
# The VIEW has _id: 0, meaning no _id field
# This means the view cannot be "updated" or "deleted" by _id
# Check if this causes issues
fr_sample = db['final_result'].find_one()
if fr_sample:
    has_id = '_id' in fr_sample
    print('  final_result has _id field: %s' % has_id)
    if not has_id:
        print('  >>> VIEW loai bo _id (project _id: 0)')
        print('  >>> Day KHONG phai nguyen nhan mat data')

print()
print('=== CONCLUSION ===')
dl_count = db['datalake_raw'].count_documents({})
fr_count = db['final_result'].count_documents({})
print('  datalake_raw: %d' % dl_count)
print('  final_result (view): %d' % fr_count)
if dl_count == fr_count:
    print('  >>> COUNTS MATCH -> View dang hien thi DUNG du lieu')
    print('  >>> Neu ban thay data moi bi mat, co the do:')
    print('  >>>   1. Frontend CACHE cu, can reload')
    print('  >>>   2. VIEW query cham khi co nhieu data')
    print('  >>>   3. Spring Boot session rebuild xoa sessions cu')
else:
    print('  >>> COUNTS MISMATCH! %d records bi VIEW loc bo' % (dl_count - fr_count))
    print('  >>> Nguyen nhan: records khong co prediction.label')

client.close()
print()
print('DONE')
