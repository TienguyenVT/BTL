# -*- coding: utf-8 -*-
"""
Kiem tra so luong records bi mat (khong co prediction)
va backfill neu can.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pymongo import MongoClient
import requests

client = MongoClient('mongodb://localhost:27017')
db = client['iomt_health_monitor']

print('=' * 60)
print('  KIEM TRA DATA BI MAT & FIX')
print('=' * 60)

# 1. Dem records khong co prediction
no_pred_count = db['datalake_raw'].count_documents({
    '$or': [
        {'prediction': None},
        {'prediction.label': None},
        {'prediction.label': {'$exists': False}}
    ]
})
total = db['datalake_raw'].count_documents({})
has_pred = db['datalake_raw'].count_documents({
    'prediction.label': {'$exists': True, '$ne': None}
})

print('\n[1] THONG KE:')
print('  Total datalake_raw: %d' % total)
print('  Co prediction.label: %d' % has_pred)
print('  KHONG co prediction (BI MAT khoi final_result): %d' % no_pred_count)

# 2. Kiem tra FastAPI co dang chay khong
print('\n[2] KIEM TRA FASTAPI /predict:')
try:
    resp = requests.get('http://localhost:8000/health', timeout=3)
    print('  Status: %d' % resp.status_code)
    print('  Response: %s' % resp.json())
    fastapi_running = True
except Exception as e:
    print('  KHONG THE KET NOI! Error: %s' % str(e))
    print('  >>> FastAPI KHONG chay -> day la nguyen nhan data moi khong co prediction!')
    fastapi_running = False

# 3. Neu co records bi mat, hien thi chi tiet
if no_pred_count > 0:
    print('\n[3] %d RECORDS BI MAT (khong co prediction):' % no_pred_count)
    missing = list(db['datalake_raw'].find({
        '$or': [
            {'prediction': None},
            {'prediction.label': None},
            {'prediction.label': {'$exists': False}}
        ]
    }).sort('ingested_at', -1).limit(10))
    
    for i, d in enumerate(missing):
        sensor = d.get('sensor', {})
        print('  [%d] ingested=%s, device=%s' % (i, d.get('ingested_at'), d.get('device_id')))
        print('      bpm=%s, spo2=%s, temp=%s, prediction=%s' % (
            sensor.get('bpm'), sensor.get('spo2'), sensor.get('body_temp'), d.get('prediction')))
    
    if no_pred_count > 10:
        print('  ... va %d records khac' % (no_pred_count - 10))
    
    # 4. Backfill neu FastAPI dang chay
    if fastapi_running:
        print('\n[4] BAT DAU BACKFILL %d records...' % no_pred_count)
        missing_all = list(db['datalake_raw'].find({
            '$or': [
                {'prediction': None},
                {'prediction.label': None},
                {'prediction.label': {'$exists': False}}
            ]
        }))
        
        success = 0
        fail = 0
        for d in missing_all:
            sensor = d.get('sensor', {})
            features = d.get('features', {})
            
            # Build payload for /predict
            payload = {
                'bpm': sensor.get('bpm', 0),
                'spo2': sensor.get('spo2', 0),
                'body_temp': sensor.get('body_temp', 0),
                'gsr_adc': sensor.get('gsr_adc', 0),
                'room_temp': sensor.get('dht11_room_temp', 0),
                'humidity': sensor.get('dht11_humidity', 0),
                'bpm_spo2_ratio': features.get('bpm_spo2_ratio', 0),
                'temp_gsr_interaction': features.get('temp_gsr_interaction', 0),
                'bpm_temp_product': features.get('bpm_temp_product', 0),
                'spo2_gsr_ratio': features.get('spo2_gsr_ratio', 0),
                'bpm_deviation': features.get('bpm_deviation', 0),
                'temp_deviation': features.get('temp_deviation', 0),
                'gsr_deviation': features.get('gsr_deviation', 0),
                'physiological_stress_index': features.get('physiological_stress_index', 0),
                'heat_index': features.get('heat_index', 0),
                'comfort_index': features.get('comfort_index', 0),
            }
            
            try:
                resp = requests.post('http://localhost:8000/predict', json=payload, timeout=5)
                if resp.status_code == 200:
                    result = resp.json()
                    # Update datalake_raw
                    db['datalake_raw'].update_one(
                        {'_id': d['_id']},
                        {'$set': {
                            'prediction': {
                                'label': result.get('predicted_label'),
                                'confidence': result.get('confidence')
                            }
                        }}
                    )
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                fail += 1
        
        print('  Backfill hoan tat: %d thanh cong, %d that bai' % (success, fail))
        
        # Verify
        new_no_pred = db['datalake_raw'].count_documents({
            '$or': [
                {'prediction': None},
                {'prediction.label': None},
                {'prediction.label': {'$exists': False}}
            ]
        })
        new_fr_count = db['final_result'].count_documents({})
        print('  SAU BACKFILL:')
        print('    Records con thieu prediction: %d' % new_no_pred)
        print('    final_result count: %d' % new_fr_count)
    else:
        print('\n[4] KHONG THE BACKFILL - FastAPI chua chay!')
        print('  Hay khoi dong FastAPI truoc:')
        print('    cd d:\\Documents\\BTL\\backend\\iot-ingestion')
        print('    python main.py')
else:
    print('\n[3] KHONG CO records bi mat! Tat ca deu co prediction.')
    print('  Neu ban van thay data mat, co the do:')
    print('    - Frontend cache cu (can hard refresh Ctrl+Shift+R)')
    print('    - MongoDB Compass can refresh lai query')
    print('    - Spring Boot session rebuild cham')

client.close()
print('\nDONE')
