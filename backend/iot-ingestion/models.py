# -*- coding: utf-8 -*-
"""
Data Models - Schema cho dữ liệu sức khỏe.
Định nghĩa cấu trúc dữ liệu thô (từ ESP32) và dữ liệu sạch (sau pipeline).

Các trường dữ liệu tương ứng với cảm biến trên ESP32:
  - BPM:              Nhịp tim (MAX30102)
  - SpO2:             Độ bão hòa oxy máu (MAX30102)
  - Body_Temp:        Nhiệt độ cơ thể (MCP9808)
  - GSR_ADC:          Điện trở da - Galvanic Skin Response (ADC)
  - Ext_Temp_C:       Nhiệt độ môi trường (DHT22)
  - Ext_Humidity_Pct: Độ ẩm môi trường (DHT22)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class TrainingHealthData:
    """
    Dữ liệu huấn luyện đã làm sạch (Training Data).
    Lưu trữ trong MongoDB (training_health_data) phục vụ cho việc train model.
    """
    user_id: str                            # ID người dùng (từ file CSV)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Cảm biến sinh lý
    bpm: float = 0.0
    spo2: float = 0.0
    body_temp: float = 0.0
    gsr_adc: float = 0.0

    # Cảm biến môi trường
    ext_temp_c: float = 0.0
    ext_humidity_pct: float = 0.0

    # Nhãn chuẩn (Ground Truth sau khi Clean)
    label: str = "Normal"
    time_slot: Optional[str] = None         # Morning | Afternoon | Evening

    def to_dict(self) -> dict:
        data = asdict(self)
        data["is_training_data"] = True
        return data


@dataclass
class RealtimeHealthData:
    """
    Dữ liệu thực tế giám sát (Real-time).
    Nhận từ ESP32 (MQTT/HTTP) -> Được Model dự đoán -> Lưu DB để Dashboard Java đọc.
    """
    device_id: str
    user_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Dữ liệu sinh lý (RAW từ ESP)
    bpm: float = 0.0
    spo2: float = 0.0
    body_temp: float = 0.0
    gsr_adc: float = 0.0

    # Dữ liệu môi trường
    ext_temp_c: float = 0.0
    ext_humidity_pct: float = 0.0

    # Nhãn được MODEL DỰ ĐOÁN (Predicted Label)
    label: str = "Normal"
    time_slot: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
