# -*- coding: utf-8 -*-
"""
Kết nối MongoDB sử dụng PyMongo.
Cung cấp singleton database client cho toàn bộ ứng dụng.

Bao gồm:
  - MongoDBConnection: Singleton quản lý kết nối
  - setup_indexes(): Tạo indexes cho raw_sensor và realtime_health_data
  - TypedDict document schemas (documentation-only)
"""

import logging
from datetime import datetime
from typing import Optional, TypedDict

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from config import settings

logger = logging.getLogger("iot-ingestion.database")


# ══════════════════════════════════════════════════════════════════════════════
# TypedDict Document Schemas (documentation only — không enforced bởi MongoDB)
# ══════════════════════════════════════════════════════════════════════════════

class RawSensorDoc(TypedDict):
    """Schema cho collection raw_sensor (Data Lake backup, TTL 30 ngày)."""
    device_id: str
    timestamp: int                  # Unix ms (từ ESP32)
    bpm: float
    spo2: float
    body_temp: float
    gsr_adc: float
    ingested_at: datetime           # ISODate — dùng cho TTL index


class RealtimeHealthDoc(TypedDict):
    """Schema cho collection realtime_health_data (Datawarehouse)."""
    device_id: str
    timestamp: int                  # Unix ms
    bpm: float
    spo2: float
    body_temp: float
    gsr_adc: float
    # 8 engineered features
    bpm_spo2_ratio: float
    temp_gsr_interaction: float
    bpm_temp_product: float
    spo2_gsr_ratio: float
    bpm_deviation: float
    temp_deviation: float
    gsr_deviation: float
    physiological_stress_index: float
    # ML prediction results
    predicted_label: Optional[str]  # None nếu predict thất bại
    confidence: Optional[float]     # None nếu predict thất bại
    ingested_at: datetime           # ISODate — thời điểm ghi vào DB


# ══════════════════════════════════════════════════════════════════════════════
# MongoDB Index Setup
# ══════════════════════════════════════════════════════════════════════════════

async def setup_indexes(db: Database) -> None:
    """
    Tạo các indexes cần thiết cho MongoDB collections.

    Collections:
      - raw_sensor: TTL 30 ngày, compound index (device_id, ingested_at)
      - realtime_health_data: compound index (device_id, timestamp), index on predicted_label

    Gọi hàm này trong FastAPI startup event.
    """
    # ── raw_sensor (Data Lake backup) ────────────────────────────────
    raw_col = db[settings.RAW_SENSOR_COLLECTION]

    # TTL index: tự động xóa documents sau 30 ngày (2592000 giây)
    # Sử dụng trường ingested_at (ISODate) thay vì timestamp (unix ms int)
    raw_col.create_index(
        [("ingested_at", ASCENDING)],
        expireAfterSeconds=2592000,  # 30 days
        name="ttl_ingested_at_30d",
    )

    # Compound index cho truy vấn theo device + thời gian
    raw_col.create_index(
        [("device_id", ASCENDING), ("ingested_at", DESCENDING)],
        name="idx_device_ingested",
    )

    logger.info("Created indexes for collection '%s'", settings.RAW_SENSOR_COLLECTION)

    # ── realtime_health_data (Datawarehouse) ─────────────────────────
    realtime_col = db[settings.REALTIME_COLLECTION]

    # Compound index cho truy vấn theo device + thời gian
    realtime_col.create_index(
        [("device_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_device_timestamp",
    )

    # Single index cho filter theo predicted_label
    realtime_col.create_index(
        [("predicted_label", ASCENDING)],
        name="idx_predicted_label",
    )

    logger.info("Created indexes for collection '%s'", settings.REALTIME_COLLECTION)


# ══════════════════════════════════════════════════════════════════════════════
# MongoDB Connection Singleton
# ══════════════════════════════════════════════════════════════════════════════

class MongoDBConnection:
    """
    Quản lý kết nối MongoDB.
    Sử dụng pattern Singleton để đảm bảo chỉ có 1 connection duy nhất.
    """

    _instance = None
    _client: MongoClient = None
    _db: Database = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._client = MongoClient(settings.MONGO_URI)
                cls._db = cls._client[settings.MONGO_DB_NAME]
                # Kiểm tra kết nối
                cls._db.command("ping")
                logger.info(
                    "Connected MongoDB: %s/%s",
                    settings.MONGO_URI,
                    settings.MONGO_DB_NAME,
                )
            except ConnectionFailure as e:
                logger.error("MongoDB connection error: %s", e)
        return cls._instance

    @property
    def database(self) -> Database:
        """Trả về database instance."""
        return self._db

    def get_training_collection(self) -> Collection:
        """Collection lưu dữ liệu mẫu huấn luyện từ CSV."""
        return self._db[settings.TRAINING_COLLECTION]

    def get_realtime_collection(self) -> Collection:
        """Collection lưu dữ liệu MQTT thực sau khi qua Model dự đoán."""
        return self._db[settings.REALTIME_COLLECTION]

    def get_raw_sensor_collection(self) -> Collection:
        """Collection lưu raw sensor data backup (Data Lake, TTL 30 ngày)."""
        return self._db[settings.RAW_SENSOR_COLLECTION]

    def close(self):
        """Đóng kết nối MongoDB."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")


# Instance duy nhất
db_connection = MongoDBConnection()
