# -*- coding: utf-8 -*-
"""
Ingestion Service - Logic cốt lõi của Module Nhận dữ liệu (Real-time).

Quy trình MỚI (chỉ phục vụ ML Prediction mượt mà):
  1. Nhận dữ liệu thô từ ESP32 (qua MQTT hoặc HTTP).
  2. Validate cơ bản (các trường bắt buộc).
  3. Load model RandomForest (.pkl) để dự đoán trực tiếp Nhãn thời gian thực (Label).
  4. Lưu dữ liệu cùng với Label đã dự đoán thẳng vào MongoDB collection `realtime_health_data`.
  
Pipeline làm sạch 5 lớp KHÔNG CHẠY LUỒNG NÀY (Chỉ chạy khi huấn luyện mô hình ở train_model.py).
"""

from typing import Dict, Any
from database import db_connection
from models import RealtimeHealthData
from ml_model.predictor import RealtimePredictor


class IngestionService:
    """Service xử lý dữ liệu MQTT giám sát hệ thống thời gian thực theo cấu trúc ML-driven."""

    REQUIRED_FIELDS = ["device_id", "user_id", "bpm", "spo2", "body_temp", "gsr_adc"]

    def __init__(self):
        # Lưu vào collection API Frontend cần
        self.realtime_col = db_connection.get_realtime_collection()
        
        # Load RF Model từ file (nếu đã train)
        self.predictor = RealtimePredictor()

    def ingest_data(self, data: Dict[str, Any]) -> None:
        """Nhận và dự đoán 1 bản ghi MQTT Stream → Lưu MongoDB trực tiếp."""
        # 1. Validate
        if not self._validate(data):
            print(f"[SERVICE] ✗ Data không hợp lệ, bỏ qua: {data}")
            return

        # 2. Dùng Model ML đã huấn luyện để phân tích và đánh Nhãn (Predict Label)
        predicted_label = self.predictor.predict(data)
        print(f"[SERVICE] 🧠 Model đã đánh nhãn: {predicted_label}")

        # 3. Tạo Object và Lưu xuống MongoDB `realtime_health_data`
        record = RealtimeHealthData(
            device_id=data["device_id"],
            user_id=data["user_id"],
            bpm=float(data["bpm"]),
            spo2=float(data["spo2"]),
            body_temp=float(data["body_temp"]),
            gsr_adc=float(data["gsr_adc"]),
            ext_temp_c=float(data.get("ext_temp_c", 0)),
            ext_humidity_pct=float(data.get("ext_humidity_pct", 0)),
            label=predicted_label
        )

        try:
            self.realtime_col.insert_one(record.to_dict())
            print(f"[SERVICE] ✓ Lưu Realtime DB => device={record.device_id} | label={predicted_label}")
        except Exception as e:
            print(f"[SERVICE] ✗ Lỗi khi lưu bản ghi realtime: {e}")

    def _validate(self, data: Dict[str, Any]) -> bool:
        """Validate các rường thiết yếu."""
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                print(f"[SERVICE] ✗ Thiếu trường bắt buộc: {field}")
                return False
        return True

    def flush_buffer(self) -> None:
        """Giữ method tương thích ngược (không còn cần thiết vì dữ liệu Realtime đẩy thẳng)."""
        pass
