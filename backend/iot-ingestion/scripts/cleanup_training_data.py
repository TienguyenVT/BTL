# -*- coding: utf-8 -*-
"""
Script dọn dẹp collection training_health_data:
- Loại bỏ 6 trường thừa: predicted_label, confidence,
  label_source, invalid_reading, gsr_threshold_used, unstable_window
"""

import os
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv()

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")
COLLECTION = "training_health_data"

FIELDS_TO_REMOVE = [
    "predicted_label",
    "confidence",
    "label_source",
    "invalid_reading",
    "gsr_threshold_used",
    "unstable_window",
]


def cleanup_training_data():
    print("=" * 60)
    print("  CLEANUP: training_health_data")
    print("=" * 60)
    print(f"  MongoDB : {MONGO_URI}")
    print(f"  Database: {MONGO_DB}")
    print(f"  Collection: {COLLECTION}")
    print(f"  Fields to remove: {FIELDS_TO_REMOVE}")

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    col = db[COLLECTION]

    # 1. Đếm tổng số documents
    total = col.count_documents({})
    print(f"\n[1] Tong so documents: {total}")

    # 2. Kiểm tra xem có document nào chứa các trường thừa không
    for field in FIELDS_TO_REMOVE:
        count = col.count_documents({field: {"$exists": True}})
        if count > 0:
            print(f"    - '{field}' ton tai trong {count} documents")
        else:
            print(f"    - '{field}' khong ton tai")

    # 3. Xác nhận còn label / intended_label
    has_label = col.count_documents({"label": {"$exists": True}})
    has_intended = col.count_documents({"intended_label": {"$exists": True}})
    print(f"\n[2] Kiem tra truong nhan (target):")
    print(f"    - 'label' ton tai: {has_label} documents")
    print(f"    - 'intended_label' ton tai: {has_intended} documents")

    # 4. Thực hiện xóa các trường thừa ($unset)
    # Chỉ unset những trường thực sự tồn tại
    existing_fields = []
    for field in FIELDS_TO_REMOVE:
        if col.count_documents({field: {"$exists": True}}) > 0:
            existing_fields.append(field)

    if existing_fields:
        unset_ops = {f: "" for f in existing_fields}
        result = col.update_many({}, {"$unset": unset_ops})
        print(f"\n[3] Da xoa {len(existing_fields)} truong thua:")
        for f in existing_fields:
            print(f"    - {f}")
        print(f"    So document da cap nhat: {result.modified_count}")
    else:
        print("\n[3] Khong co truong nao de xoa.")

    # 5. Kiểm tra lại sau khi xóa
    print(f"\n[4] Kiem tra sau khi xoa:")
    remaining = 0
    for field in FIELDS_TO_REMOVE:
        count = col.count_documents({field: {"$exists": True}})
        if count > 0:
            print(f"    - '{field}' CON TON TAI ({count})")
            remaining += 1
        else:
            print(f"    - '{field}' DA BI XOA")

    if remaining == 0:
        print("\n[OK] Tat ca cac truong thua da duoc xoa thanh cong!")
    else:
        print(f"\n[WARN] Con {remaining} truong chua duoc xoa.")

    # 6. Lấy 1 document mẫu để kiểm tra
    print(f"\n[5] Mot document mau sau khi cleanup:")
    sample = col.find_one({}, {"_id": 0})
    if sample:
        for k, v in sample.items():
            print(f"    {k}: {v}")
    else:
        print("    Collection rong.")

    client.close()
    print("\n" + "=" * 60)
    print("  HOAN TAT!")
    print("=" * 60)


if __name__ == "__main__":
    cleanup_training_data()
