# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['iomt_health_monitor']

print('=== COUNTS ===')
for c in ['datalake_raw', 'realtime_health_data', 'final_result']:
    try:
        cnt = db[c].count_documents({})
        print('  %s: %d' % (c, cnt))
    except Exception as e:
        print('  %s: ERROR %s' % (c, e))

print()
print('=== DATALAKE_RAW PREDICTION STATUS ===')
total = db['datalake_raw'].count_documents({})
has_pred = db['datalake_raw'].count_documents({'prediction.label': {'$exists': True, '$ne': None}})
no_pred = total - has_pred
print('  Total: %d' % total)
print('  Has prediction.label: %d' % has_pred)
print('  NO prediction.label: %d' % no_pred)

print()
print('=== final_result VIEW INFO ===')
for c in db.list_collections():
    if c['name'] == 'final_result':
        ctype = c.get('type', '?')
        print('  Type: %s' % ctype)
        opts = c.get('options', {})
        von = opts.get('viewOn', 'N/A')
        print('  ViewOn: %s' % von)
        pipeline = opts.get('pipeline', [])
        for i, s in enumerate(pipeline):
            k = list(s.keys())[0]
            print('  Stage %d: %s = %s' % (i, k, s[k]))

print()
print('=== 5 NEWEST datalake_raw ===')
for i, d in enumerate(db['datalake_raw'].find().sort('ingested_at', -1).limit(5)):
    pred = d.get('prediction')
    ingested = d.get('ingested_at')
    device = d.get('device_id')
    source = d.get('source')
    print('  [%d] ingested=%s, pred=%s, device=%s, source=%s' % (i, ingested, pred, device, source))

print()
print('=== 5 NEWEST final_result ===')
for i, d in enumerate(db['final_result'].find().limit(5)):
    ingested = d.get('ingested_at')
    label = d.get('label')
    bpm = d.get('bpm')
    print('  [%d] ingested=%s, label=%s, bpm=%s' % (i, ingested, label, bpm))

print()
print('=== CAPPED/TTL CHECK ===')
for c in ['datalake_raw', 'realtime_health_data']:
    try:
        stats = db.command('collStats', c)
        capped = stats.get('capped')
        storage = stats.get('storageSize')
        print('  %s: capped=%s, storageSize=%s' % (c, capped, storage))
        idxs = db[c].index_information()
        for n, info in idxs.items():
            if 'expireAfterSeconds' in info:
                ttl = info['expireAfterSeconds']
                print('    TTL index: %s = %ds (%.1fh)' % (n, ttl, ttl/3600.0))
    except Exception as e:
        print('  %s: ERROR %s' % (c, e))

print()
print('=== LAST 20 RECORDS PREDICTION STATUS ===')
newest = list(db['datalake_raw'].find().sort('ingested_at', -1).limit(20))
ok = sum(1 for d in newest if d.get('prediction') and d['prediction'].get('label'))
fail = len(newest) - ok
print('  OK (has prediction.label): %d' % ok)
print('  FAIL (no prediction.label): %d' % fail)

if fail > 0:
    print()
    print('>>> ROOT CAUSE: Data moi KHONG co prediction.label')
    print('>>> final_result VIEW chi hien thi records CO prediction.label')
    print('>>> KHI dung hardware, neu /predict API fail -> data luu vao datalake_raw NHUNG prediction=null')
    print('>>> -> VIEW final_result LOC BO cac records nay!')
    print()
    print('FIX: Kiem tra FastAPI /predict (port 8000) co dang chay khong')

client.close()
print()
print('DONE')
