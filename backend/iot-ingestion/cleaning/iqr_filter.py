# -*- coding: utf-8 -*-
"""
Lớp 2: Phát hiện ngoại lai thống kê (IQR per Label).

Nguyên lý:
  - Tính IQR (Interquartile Range) riêng cho từng nhóm nhãn.
  - Giá trị nằm ngoài [Q1 - 1.5*IQR, Q3 + 1.5*IQR] → NaN.
  - Sau đó nội suy tuyến tính (Linear Interpolation) để lấp NaN.

Tham khảo: Health_Analysis.py - Lớp 2
"""

import numpy as np
import pandas as pd


# Các trường áp dụng lọc IQR
IQR_FEATURES = ["bpm", "spo2", "body_temp", "gsr_adc"]


def apply_iqr_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lọc ngoại lai bằng phương pháp IQR theo từng nhóm nhãn.
    Giá trị ngoại lai → NaN → nội suy tuyến tính.

    Args:
        df: DataFrame đã qua Lớp 1

    Returns:
        DataFrame đã lọc ngoại lai và nội suy
    """
    print("  [Lớp 2] Đang lọc ngoại lai IQR theo nhãn...")

    iqr_nan_count = 0
    label_col = "label" if "label" in df.columns else None

    # Nếu không có nhãn, áp dụng IQR toàn cục
    labels = df[label_col].unique() if label_col else ["ALL"]

    for label in labels:
        label_mask = df[label_col] == label if label_col else pd.Series(True, index=df.index)

        for col in IQR_FEATURES:
            if col not in df.columns:
                continue

            subset = df.loc[label_mask, col].dropna()
            if len(subset) < 10:
                continue

            Q1 = subset.quantile(0.25)
            Q3 = subset.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR

            outlier_mask = label_mask & ((df[col] < lower) | (df[col] > upper))
            n_outliers = outlier_mask.sum()

            if n_outliers > 0:
                df.loc[outlier_mask, col] = np.nan
                iqr_nan_count += n_outliers

    print(f"    Tổng giá trị NaN hóa bởi IQR: {iqr_nan_count}")

    # Nội suy tuyến tính để lấp NaN
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit_direction="both")
    df[numeric_cols] = df[numeric_cols].bfill().ffill()

    print(f"    ✓ Đã nội suy tuyến tính lấp đầy NaN")
    return df
