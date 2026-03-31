# -*- coding: utf-8 -*-
"""
Cấu hình ứng dụng - Load từ biến môi trường (.env).
Tập trung quản lý tất cả settings tại một nơi duy nhất.
"""

import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()


class Settings:
    """Singleton chứa toàn bộ cấu hình ứng dụng."""

    # ── MongoDB ──────────────────────────────────────────────────────────
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

    # Tên các collection trong MongoDB
    TRAINING_COLLECTION: str = "training_health_data" # Dữ liệu mẫu (CSV sau khi làm sạch) dùng để huấn luyện
    REALTIME_COLLECTION: str = "realtime_health_data" # Dữ liệu thực MQTT sau khi dự đoán nhãn
    RAW_SENSOR_COLLECTION: str = "raw_sensor"          # Data Lake backup (TTL 30 ngày)

    # ── MQTT Broker ──────────────────────────────────────────────────────
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "esp32/health/data")
    MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "iomt-ingestion-service")

    # ── HTTP Server (FastAPI) ────────────────────────────────────────────
    HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT: int = int(os.getenv("HTTP_PORT", "8000"))

    # ── Machine Learning & Cleaning ──────────────────────────────────────────────
    ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "ml_model/random_forest.pkl")
    CSV_DATA_PATH: str = os.getenv("CSV_DATA_PATH", "../../Data/health_data_all.csv")


# Instance duy nhất dùng xuyên suốt ứng dụng
settings = Settings()
