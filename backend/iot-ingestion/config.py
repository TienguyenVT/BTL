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
    TRAINING_COLLECTION: str = "training_health_data" # Du lieu mau (CSV sau khi lam sach) dung de huan luyen
    REALTIME_COLLECTION: str = "realtime_health_data"  # Datawarehouse: 12 engineered features + DHT11
    DATALAKE_COLLECTION: str = "datalake_raw"          # Data Lake: raw MQTT payload + rich metadata (khong TTL)
    FINAL_RESULT_COLLECTION: str = "final_result"     # Ket qua cuoi cung: sensor data + label + timestamp

    # ── DHT11 Sensor (room environment) ──────────────────────────────────────
    DHT11_ROOM_TEMP_FIELD: str = "room_temp"  # ten truong nhiet do phong
    DHT11_HUMIDITY_FIELD: str = "humidity"    # ten truong do am

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
