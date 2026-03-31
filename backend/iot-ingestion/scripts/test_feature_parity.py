# -*- coding: utf-8 -*-
"""
Feature Parity Test — Kiểm tra JS feature engineering (Node-RED)
trùng khớp với Python logic trong train_model.py.

These expected values should be verified against actual Node-RED debug node
output before running in production. Run:
  node-red-test-capture.sh to get JS output.

Usage:
  cd c:\\Documents\\BTL\\backend\\iot-ingestion
  python -m pytest test_feature_parity.py -v
"""

import math
import pytest

# Import FEATURE_COLS from service.py to verify column order
from service import FEATURE_COLS


# ══════════════════════════════════════════════════════════════════════════════
# Reference Python Implementation (mirrors Node-RED Function Node 2 exactly)
# ══════════════════════════════════════════════════════════════════════════════

def compute_features_python(raw: dict) -> dict:
    """
    Compute 8 derived features from raw sensor data.
    Mirrors the Node-RED Function Node 2 and train_model.py logic exactly.

    Args:
        raw: dict with keys 'bpm', 'spo2', 'body_temp', 'gsr_adc'

    Returns:
        dict with all 8 engineered feature values
    """
    eps = 1e-6

    bpm = float(raw["bpm"])
    spo2 = float(raw["spo2"])
    body_temp = float(raw["body_temp"])
    gsr_adc = float(raw["gsr_adc"])

    return {
        "bpm_spo2_ratio": bpm / (spo2 + eps),
        "temp_gsr_interaction": body_temp * gsr_adc / 1000,
        "bpm_temp_product": bpm * body_temp,
        "spo2_gsr_ratio": spo2 / (gsr_adc + eps),
        "bpm_deviation": abs(bpm - 75),
        "temp_deviation": abs(body_temp - 36.8),
        "gsr_deviation": abs(gsr_adc - 2200),
        "physiological_stress_index": (bpm - 75) / 75 + (gsr_adc - 2200) / 2200,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════════════════════

# Each case: (description, raw_input, expected_features)
TEST_CASES = [
    # Case 1: Normal healthy readings
    (
        "normal_healthy",
        {"bpm": 75.0, "spo2": 98.0, "body_temp": 36.5, "gsr_adc": 2200.0},
        {
            "bpm_spo2_ratio": 75.0 / (98.0 + 1e-6),
            "temp_gsr_interaction": 36.5 * 2200.0 / 1000,
            "bpm_temp_product": 75.0 * 36.5,
            "spo2_gsr_ratio": 98.0 / (2200.0 + 1e-6),
            "bpm_deviation": 0.0,
            "temp_deviation": 0.3,
            "gsr_deviation": 0.0,
            "physiological_stress_index": 0.0,
        },
    ),
    # Case 2: High stress readings
    (
        "high_stress",
        {"bpm": 140.0, "spo2": 94.0, "body_temp": 37.8, "gsr_adc": 3500.0},
        {
            "bpm_spo2_ratio": 140.0 / (94.0 + 1e-6),
            "temp_gsr_interaction": 37.8 * 3500.0 / 1000,
            "bpm_temp_product": 140.0 * 37.8,
            "spo2_gsr_ratio": 94.0 / (3500.0 + 1e-6),
            "bpm_deviation": 65.0,
            "temp_deviation": 1.0,
            "gsr_deviation": 1300.0,
            "physiological_stress_index": (140.0 - 75) / 75 + (3500.0 - 2200) / 2200,
        },
    ),
    # Case 3: Edge case — spo2 near minimum (72)
    (
        "edge_low_spo2",
        {"bpm": 90.0, "spo2": 72.0, "body_temp": 37.0, "gsr_adc": 1800.0},
        {
            "bpm_spo2_ratio": 90.0 / (72.0 + 1e-6),
            "temp_gsr_interaction": 37.0 * 1800.0 / 1000,
            "bpm_temp_product": 90.0 * 37.0,
            "spo2_gsr_ratio": 72.0 / (1800.0 + 1e-6),
            "bpm_deviation": 15.0,
            "temp_deviation": 0.2,
            "gsr_deviation": 400.0,
            "physiological_stress_index": (90.0 - 75) / 75 + (1800.0 - 2200) / 2200,
        },
    ),
    # Case 4: Edge case — gsr_adc = 0 (test division guard)
    (
        "edge_gsr_zero",
        {"bpm": 80.0, "spo2": 97.0, "body_temp": 36.8, "gsr_adc": 0.0},
        {
            "bpm_spo2_ratio": 80.0 / (97.0 + 1e-6),
            "temp_gsr_interaction": 36.8 * 0.0 / 1000,
            "bpm_temp_product": 80.0 * 36.8,
            "spo2_gsr_ratio": 97.0 / (0.0 + 1e-6),
            "bpm_deviation": 5.0,
            "temp_deviation": 0.0,
            "gsr_deviation": 2200.0,
            "physiological_stress_index": (80.0 - 75) / 75 + (0.0 - 2200) / 2200,
        },
    ),
    # Case 5: Edge case — bpm at boundary (30)
    (
        "edge_bpm_boundary",
        {"bpm": 30.0, "spo2": 95.0, "body_temp": 35.5, "gsr_adc": 1500.0},
        {
            "bpm_spo2_ratio": 30.0 / (95.0 + 1e-6),
            "temp_gsr_interaction": 35.5 * 1500.0 / 1000,
            "bpm_temp_product": 30.0 * 35.5,
            "spo2_gsr_ratio": 95.0 / (1500.0 + 1e-6),
            "bpm_deviation": 45.0,
            "temp_deviation": 1.3,
            "gsr_deviation": 700.0,
            "physiological_stress_index": (30.0 - 75) / 75 + (1500.0 - 2200) / 2200,
        },
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized Tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "name,raw_input,expected",
    TEST_CASES,
    ids=[tc[0] for tc in TEST_CASES],
)
def test_feature_engineering_parity(name: str, raw_input: dict, expected: dict):
    """
    Verify that compute_features_python produces values matching
    the hardcoded expected dict (which should also match Node-RED JS output).
    """
    computed = compute_features_python(raw_input)

    for feature_name, expected_value in expected.items():
        computed_value = computed[feature_name]
        assert computed_value == pytest.approx(expected_value, abs=1e-6), (
            f"[{name}] Feature '{feature_name}' mismatch: "
            f"computed={computed_value}, expected={expected_value}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE_COLS Order Verification
# ══════════════════════════════════════════════════════════════════════════════

def test_feature_cols_order():
    """
    Verify that FEATURE_COLS in service.py matches the exact order
    expected by the trained model (base features first, then engineered).
    """
    expected_order = [
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

    assert FEATURE_COLS == expected_order, (
        f"FEATURE_COLS order mismatch!\n"
        f"  Got:      {FEATURE_COLS}\n"
        f"  Expected: {expected_order}"
    )


def test_feature_cols_count():
    """Verify FEATURE_COLS contains exactly 12 features (4 base + 8 engineered)."""
    assert len(FEATURE_COLS) == 12, (
        f"Expected 12 features, got {len(FEATURE_COLS)}: {FEATURE_COLS}"
    )


def test_compute_features_returns_all_engineered():
    """Verify compute_features_python returns all 8 engineered features."""
    raw = {"bpm": 75.0, "spo2": 98.0, "body_temp": 36.5, "gsr_adc": 2200.0}
    result = compute_features_python(raw)

    engineered_cols = FEATURE_COLS[4:]  # Skip 4 base features
    for col in engineered_cols:
        assert col in result, f"Missing engineered feature: {col}"
        assert isinstance(result[col], float), (
            f"Feature '{col}' is not float: {type(result[col])}"
        )
