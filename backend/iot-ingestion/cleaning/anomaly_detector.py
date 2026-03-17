# -*- coding: utf-8 -*-
"""
Lớp 3: Phát hiện bất thường đa biến (Isolation Forest + LOF đồng thuận).

Nguyên lý:
  - Sử dụng 2 thuật toán phát hiện anomaly: Isolation Forest & Local Outlier Factor.
  - Chỉ loại bỏ bản ghi khi CẢ HAI thuật toán đều đánh dấu là anomaly (đồng thuận).
  - Điều này giảm false positive so với dùng 1 thuật toán.

Tham khảo: Health_Analysis.py - Lớp 3
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


# Các trường dùng cho phát hiện anomaly
ANOMALY_FEATURES = ["bpm", "spo2", "body_temp", "gsr_adc"]

# Tỷ lệ contamination (tỷ lệ dữ liệu bất thường dự kiến)
CONTAMINATION_RATE = 0.05


def apply_anomaly_detection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phát hiện và loại bỏ anomaly bằng đồng thuận IF + LOF.

    Args:
        df: DataFrame đã qua Lớp 2

    Returns:
        DataFrame đã loại bỏ các bản ghi anomaly
    """
    print("  [Lớp 3] Đang phát hiện bất thường đa biến (IF + LOF)...")

    total_dropped = 0
    label_col = "label" if "label" in df.columns else None
    labels = df[label_col].unique() if label_col else ["ALL"]

    for label in labels:
        label_idx = df[df[label_col] == label].index if label_col else df.index

        # Cần tối thiểu 30 mẫu để thuật toán hoạt động chính xác
        if len(label_idx) < 30:
            print(f"    [{label}] Bỏ qua - không đủ dữ liệu ({len(label_idx)} mẫu)")
            continue

        X_label = df.loc[label_idx, ANOMALY_FEATURES].copy()

        # Chuẩn hóa dữ liệu (Z-score)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_label)

        # Isolation Forest
        iso_forest = IsolationForest(contamination=CONTAMINATION_RATE, random_state=42, n_jobs=-1)
        iso_pred = iso_forest.fit_predict(X_scaled)

        # Local Outlier Factor
        lof = LocalOutlierFactor(n_neighbors=20, contamination=CONTAMINATION_RATE)
        lof_pred = lof.fit_predict(X_scaled)

        # Đồng thuận: loại KHI CẢ HAI đánh dấu anomaly (-1)
        consensus = (iso_pred == -1) & (lof_pred == -1)
        n_anomalies = consensus.sum()

        if n_anomalies > 0:
            drop_idx = label_idx[consensus]
            df = df.drop(drop_idx)
            total_dropped += n_anomalies
            print(f"    [{label}] Loại bỏ {n_anomalies} anomaly đồng thuận")

    print(f"    Tổng bản ghi loại bỏ: {total_dropped} | Còn lại: {len(df)}")
    return df
