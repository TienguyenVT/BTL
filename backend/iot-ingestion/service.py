# -*- coding: utf-8 -*-
"""
Ingestion Service — Logic cốt lõi cho ML Prediction endpoint.

Quy trình MỚI (HTTP /predict):
  1. Node-RED gửi dữ liệu đã cleansed + engineered features qua HTTP POST.
  2. Service load model .pkl (cached) và predict label + confidence.
  3. Trả kết quả về cho Node-RED, Node-RED tự ghi vào MongoDB.

Feature columns MUST match the order used in train_model.py exactly.
"""

import logging
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np

from config import settings

logger = logging.getLogger("iot-ingestion.service")

# ── Feature columns (must match train_model.py feature order exactly) ────────
FEATURE_COLS: list[str] = [
    "bpm",
    "spo2",
    "body_temp",
    "gsr_adc",
    "bpm_spo2_ratio",
    "temp_gsr_interaction",
    "bpm_temp_product",
    "spo2_gsr_ratio",
    "bpm_deviation",
    "temp_deviation",
    "gsr_deviation",
    "physiological_stress_index",
]

# ── Model cache ──────────────────────────────────────────────────────────────
_model_cache: Optional[Dict[str, Any]] = None


def get_model() -> Dict[str, Any]:
    """
    Load the .pkl model file once and cache it in memory.

    Returns:
        Dictionary containing 'model', 'model_type', and optionally 'label_encoder'.

    Raises:
        FileNotFoundError: If the .pkl file does not exist.
        RuntimeError: If the .pkl file is corrupt or cannot be loaded.
    """
    global _model_cache

    if _model_cache is not None:
        return _model_cache

    model_path: str = settings.ML_MODEL_PATH
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file not found at '{model_path}'. "
            "Run 'python train_model.py' to train and save the model first."
        )

    try:
        loaded = joblib.load(model_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to load model from '{model_path}': {exc}") from exc

    # Handle both new dict-format and legacy bare-model format
    if isinstance(loaded, dict):
        _model_cache = {
            "model": loaded["model"],
            "model_type": loaded.get("model_type", "randomforest"),
            "label_encoder": loaded.get("label_encoder"),
        }
        logger.info(
            "Loaded %s model (version %s)",
            _model_cache["model_type"],
            loaded.get("version", "unknown"),
        )
    else:
        _model_cache = {
            "model": loaded,
            "model_type": "randomforest",
            "label_encoder": None,
        }
        logger.info("Loaded legacy RandomForest model")

    return _model_cache


async def predict_health_label(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict health label from a feature-engineered payload.

    Args:
        payload: Dict with keys matching FEATURE_COLS.

    Returns:
        Dict with 'predicted_label' (str) and 'confidence' (float 0.0–1.0).
    """
    model_info = get_model()
    model = model_info["model"]
    model_type = model_info["model_type"]
    label_encoder = model_info["label_encoder"]

    # Build feature array in the exact column order the model expects
    feature_values = [float(payload[col]) for col in FEATURE_COLS]
    X = np.array([feature_values])

    # Predict
    if model_type == "xgboost" and label_encoder is not None:
        encoded_pred = model.predict(X)
        predicted_label = label_encoder.inverse_transform(
            np.array(encoded_pred).astype(int)
        )[0]
        # XGBoost predict_proba
        probas = model.predict_proba(X)[0]
        confidence = float(np.max(probas))
    else:
        predicted_label = model.predict(X)[0]
        probas = model.predict_proba(X)[0]
        confidence = float(np.max(probas))

    return {
        "predicted_label": str(predicted_label),
        "confidence": round(confidence, 4),
    }
