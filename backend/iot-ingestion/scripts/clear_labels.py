# -*- coding: utf-8 -*-
"""
Xóa nhãn dự đoán (predicted_label, confidence) khỏi collection realtime_health_data.
Giữ nguyên dữ liệu sensor gốc và 8 engineered features để train lại ML model.
"""

import sys
sys.path.insert(0, "C:/Documents/BTL/backend/iot-ingestion")

from dotenv import load_dotenv
load_dotenv("C:/Documents/BTL/backend/iot-ingestion/.env")

from pymongo import MongoClient, DESCENDING
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")
COLLECTION_NAME = "realtime_health_data"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print(f"Ket noi thanh cong den MongoDB: {MONGO_URI}")
except Exception as e:
    print(f"Loi ket noi MongoDB: {e}")
    sys.exit(1)

db = client[MONGO_DB]
col = db[COLLECTION_NAME]

# Đếm trước khi xóa
total_before = col.count_documents({})
has_label = col.count_documents({"predicted_label": {"$ne": None}})
has_confidence = col.count_documents({"confidence": {"$ne": None}})

print(f"\n--- Thong ke truoc khi cap nhat ---")
print(f"Tong so mau: {total_before}")
print(f"  - Co predicted_label: {has_label}")
print(f"  - Co confidence: {has_confidence}")

# Cập nhật: xóa predicted_label và confidence bằng $unset
result = col.update_many(
    {},
    {"$unset": {"predicted_label": "", "confidence": ""}}
)

print(f"\n--- Ket qua cap nhat ---")
print(f"Da cap nhat: {result.modified_count} mau (set predicted_label=None, confidence=None)")

# Kiểm tra sau khi xóa
total_after = col.count_documents({})
has_label_after = col.count_documents({"predicted_label": {"$ne": None}})
has_confidence_after = col.count_documents({"confidence": {"$ne": None}})

print(f"\n--- Thong ke sau khi cap nhat ---")
print(f"Tong so mau: {total_after}")
print(f"  - Con predicted_label: {has_label_after}")
print(f"  - Con confidence: {has_confidence_after}")

# Xem sample sau khi xóa
print(f"\n--- 3 mau sau khi xoa nhan ---")
for doc in col.find().sort("timestamp", DESCENDING).limit(3):
    doc.pop("_id", None)
    print(doc)

# Thống kê distribution nhãn cũ (lấy từ backup nếu cần)
# (Khong co truong predicted_label con lai -> khong thong ke duoc nua)

print("\nDa hoan tat. Du lieu san sang de train lai ML model.")
client.close()