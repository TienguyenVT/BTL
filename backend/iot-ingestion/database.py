# -*- coding: utf-8 -*-
"""
Kết nối MongoDB sử dụng PyMongo.
Cung cấp singleton database client cho toàn bộ ứng dụng.
"""

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure
from config import settings


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
                cls._db.command('ping')
                print(f"[DB] [OK] Connected MongoDB: {settings.MONGO_URI}/{settings.MONGO_DB_NAME}")
            except ConnectionFailure as e:
                print(f"[DB] [FAIL] MongoDB connection error: {e}")
                # Optionally, re-raise the exception or handle it differently
                # For now, we'll just print the error and the _db might be uninitialized or invalid
                # if the connection truly failed.
                # A more robust solution might set _db to None and have methods check for it.
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

    def close(self):
        """Đóng kết nối MongoDB."""
        if self._client:
            self._client.close()
            print("[DB] MongoDB connection closed.")


# Instance duy nhất
db_connection = MongoDBConnection()
