# -*- coding: utf-8 -*-
"""
Pydantic Schemas — Request/Response models cho FastAPI endpoints.

PredictRequest:  Dữ liệu đã cleansed + engineered features từ Node-RED.
PredictResponse: Kết quả dự đoán nhãn sức khỏe từ ML model.
"""

from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    """Schema cho POST /predict — Nhận dữ liệu đã feature-engineered từ Node-RED."""

    # ── Raw sensor fields ────────────────────────────────────────────
    bpm: float = Field(..., description="Nhịp tim (MAX30102)")
    spo2: float = Field(..., description="Độ bão hòa oxy máu (MAX30102)")
    body_temp: float = Field(..., description="Nhiệt độ cơ thể (MCP9808)")
    gsr_adc: float = Field(..., description="Điện trở da - Galvanic Skin Response (ADC)")

    # ── DHT11 fields (room environment) ─────────────────────────────
    room_temp: float = Field(
        default=0.0,
        description="Nhiệt độ phòng (DHT11, Celsius)"
    )
    humidity: float = Field(
        default=0.0,
        description="Độ ẩm không khí (DHT11, %)"
    )

    # ── Engineered features (computed by Node-RED, mirrors train_model.py) ──
    bpm_spo2_ratio: float = Field(..., description="bpm / (spo2 + eps)")
    temp_gsr_interaction: float = Field(..., description="body_temp * gsr_adc / 1000")
    bpm_temp_product: float = Field(..., description="bpm * body_temp")
    spo2_gsr_ratio: float = Field(..., description="spo2 / (gsr_adc + eps)")
    bpm_deviation: float = Field(..., description="abs(bpm - 75)")
    temp_deviation: float = Field(..., description="abs(body_temp - 36.8)")
    gsr_deviation: float = Field(..., description="abs(gsr_adc - 2200)")
    physiological_stress_index: float = Field(
        ..., description="(bpm - 75)/75 + (gsr_adc - 2200)/2200"
    )
    # ── DHT11 engineered features ───────────────────────────────────
    heat_index: float = Field(
        default=0.0,
        description="Chỉ số nhiệt = body_temp + 0.05 * humidity (DHT11)"
    )
    comfort_index: float = Field(
        default=0.0,
        description="Chỉ số thoải mái môi trường, -1..1 (DHT11)"
    )

    # ── Metadata ─────────────────────────────────────────────────────
    device_id: str = Field(..., description="ID thiết bị ESP32")
    timestamp: Union[int, float, str] = Field(
        default_factory=lambda: int(datetime.now().timestamp() * 1000),
        description="Unix timestamp (milliseconds) hoặc string datetime"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str):
            try:
                return int(datetime.fromisoformat(v.replace(" - ", "T")).timestamp() * 1000)
            except ValueError:
                try:
                    dt = datetime.strptime(v, "%Y:%m:%d - %H:%M:%S")
                    return int(dt.timestamp() * 1000)
                except ValueError:
                    return int(datetime.now().timestamp() * 1000)
        return int(datetime.now().timestamp() * 1000)

    model_config = {"json_schema_extra": {
        "example": {
            "bpm": 75.0, "spo2": 98.0, "body_temp": 36.5, "gsr_adc": 2200.0,
            "room_temp": 25.0, "humidity": 60.0,
            "bpm_spo2_ratio": 0.7653,
            "temp_gsr_interaction": 80.3,
            "bpm_temp_product": 2737.5,
            "spo2_gsr_ratio": 0.04454,
            "bpm_deviation": 0.0,
            "temp_deviation": 0.3,
            "gsr_deviation": 0.0,
            "physiological_stress_index": 0.0,
            "heat_index": 36.5,
            "comfort_index": 0.75,
            "device_id": "esp32_001",
            "timestamp": 1711612800000
        }
    }}


class PredictResponse(BaseModel):
    """Schema cho response POST /predict."""
    predicted_label: str = Field(..., description="Nhãn dự đoán: Normal, Stress, Fever...")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy (0.0 – 1.0)")
