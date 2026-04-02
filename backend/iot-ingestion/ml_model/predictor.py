# -*- coding: utf-8 -*-
"""
Machine Learning Predictor.

Chịu trách nhiệm load model (RandomForest hoặc XGBoost) đã được huấn luyện (từ train_model.py).
Cung cấp phương thức để dự đoán nhãn thời gian thực cho dữ liệu vừa nhận từ MQTT.

Hỗ trợ cả RandomForest và XGBoost models.
"""

import os
import joblib
import pandas as pd
from typing import Dict, Any

from config import settings


class RealtimePredictor:
    """Helper class load model và dự đoán cho stream data."""

    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.model_type = 'randomforest'  # 'randomforest' hoặc 'xgboost'
        self.is_loaded = False
        self._load_model()

    def _create_engineered_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo engineered features giống như trong training.
        Cần thiết vì model được train với features mới.
        """
        df_engineered = df.copy()

        # Tỷ lệ BPM/SPO2
        df_engineered['bpm_spo2_ratio'] = df_engineered['bpm'] / (df_engineered['spo2'] + 1e-6)

        # Tương tác nhiệt độ và GSR
        df_engineered['temp_gsr_interaction'] = df_engineered['body_temp'] * df_engineered['gsr_adc'] / 1000

        # Tích BPM và nhiệt độ
        df_engineered['bpm_temp_product'] = df_engineered['bpm'] * df_engineered['body_temp']

        # Tỷ lệ SpO2/GSR
        df_engineered['spo2_gsr_ratio'] = df_engineered['spo2'] / (df_engineered['gsr_adc'] + 1e-6)

        # Độ lệch BPM so với baseline Normal (~75)
        df_engineered['bpm_deviation'] = abs(df_engineered['bpm'] - 75)

        # Độ lệch nhiệt độ so với baseline Normal (~36.8)
        df_engineered['temp_deviation'] = abs(df_engineered['body_temp'] - 36.8)

        # Độ lệch GSR so với baseline Normal (~2200)
        df_engineered['gsr_deviation'] = abs(df_engineered['gsr_adc'] - 2200)

        # Chỉ số stress tổng hợp
        df_engineered['physiological_stress_index'] = (
            (df_engineered['bpm'] - 75) / 75 +
            (df_engineered['gsr_adc'] - 2200) / 2200
        )

        return df_engineered

    def _load_model(self):
        """Tải mô hình từ file pkl vào bộ nhớ."""
        if os.path.exists(settings.ML_MODEL_PATH):
            try:
                loaded = joblib.load(settings.ML_MODEL_PATH)

                # Kiểm tra xem là dict (mới) hay chỉ là model (legacy)
                if isinstance(loaded, dict):
                    self.model = loaded.get('model')
                    self.label_encoder = loaded.get('label_encoder')
                    self.model_type = loaded.get('model_type', 'randomforest')
                    model_version = loaded.get('version', 'unknown')
                    print(f"[ML-PREDICTOR] ✓ Đã tải mô hình {self.model_type.upper()} (version: {model_version})")
                else:
                    # Legacy: chỉ là RandomForest model
                    self.model = loaded
                    self.model_type = 'randomforest'
                    print(f"[ML-PREDICTOR] ✓ Đã tải mô hình RandomForest (legacy)")

                self.is_loaded = True
            except Exception as e:
                print(f"[ML-PREDICTOR] ✗ Lỗi tải mô hình: {e}")
        else:
            print(f"[ML-PREDICTOR] ⚠ Không tìm thấy mô hình tại {settings.ML_MODEL_PATH}")
            print("[ML-PREDICTOR] Vui lòng chạy 'python train_model.py' trước!")

    def predict(self, data: Dict[str, Any]) -> str:
        """
        Dự đoán trạng thái sức khỏe cho 1 khung dữ liệu.

        Args:
            data: Payload Dict nhận từ MQTT/ESP32.

        Returns:
            Nhãn dự đoán: 'Normal', 'Stress', 'Fever' (Mặc định 'Normal' nếu fail)
        """
        if not self.is_loaded or self.model is None:
            return "Normal"  # Fallback

        try:
            # Tạo DataFrame với base features
            base_features = pd.DataFrame([{
                'bpm': float(data.get('bpm', 0)),
                'spo2': float(data.get('spo2', 0)),
                'body_temp': float(data.get('body_temp', 0)),
                'gsr_adc': float(data.get('gsr_adc', 0)),
                # DHT11 — default 0 neu khong co, model cu van hoat dong
                'room_temp': float(data.get('room_temp', 0)),
                'humidity': float(data.get('humidity', 0)),
                # DHT11 engineered features — default 0 neu khong co
                'heat_index': float(data.get('heat_index', 0)),
                'comfort_index': float(data.get('comfort_index', 0)),
            }])

            # Tạo engineered features
            features = self._create_engineered_features(base_features)

            # Dự đoán
            if self.model_type == 'xgboost' and self.label_encoder is not None:
                # XGBoost: cần encode labels trước
                import numpy as np
                encoded_pred = self.model.predict(features)
                prediction = self.label_encoder.inverse_transform(
                    np.array(encoded_pred).astype(int)
                )
                return prediction[0]
            else:
                # RandomForest: predict trực tiếp
                prediction = self.model.predict(features)
                return prediction[0]

        except Exception as e:
            print(f"[ML-PREDICTOR] ✗ Lỗi khi dự đoán: {e}")
            return "Normal"
