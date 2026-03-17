# -*- coding: utf-8 -*-
"""
Lớp 1: Lọc giới hạn sinh lý (Hard Rule Filtering).

Nguyên lý:
  - Các chỉ số sinh lý có giới hạn vật lý/sinh lý rõ ràng.
  - Giá trị ngoài giới hạn được coi là lỗi cảm biến → chuyển thành NaN.
  - Bản ghi có nhãn "Error" bị loại bỏ hoàn toàn.

Tham khảo: Health_Analysis.py - Lớp 1
"""

import numpy as np
import pandas as pd


# Ngưỡng sinh lý hợp lệ cho từng chỉ số
PHYSIOLOGICAL_LIMITS = {
    "bpm":              (40, 200),       # Nhịp tim: 40-200 BPM
    "spo2":             (80, 100),       # SpO2: 80-100%
    "body_temp":        (34, 42),        # Nhiệt độ cơ thể: 34-42°C
    "gsr_adc":          (0.01, np.inf),  # Điện trở da: > 0
    "ext_temp_c":       (-10, 50),       # Nhiệt độ ngoài: -10 to 50°C
    "ext_humidity_pct": (0, 100),        # Độ ẩm: 0-100%
}


def apply_hard_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Áp dụng bộ lọc giới hạn sinh lý.

    Bước 1a: Loại bỏ bản ghi có nhãn 'Error'
    Bước 1b: Giá trị ngoài ngưỡng → NaN

    Args:
        df: DataFrame chứa dữ liệu sức khỏe thô

    Returns:
        DataFrame đã lọc theo giới hạn sinh lý
    """
    print("  [Lớp 1] Đang lọc giới hạn sinh lý...")

    # Bước 1a: Loại bỏ nhãn "Error" (nếu có)
    if "label" in df.columns:
        error_count = (df["label"] == "Error").sum()
        df = df[df["label"] != "Error"].copy()
        if error_count > 0:
            print(f"    ✗ Loại bỏ {error_count} bản ghi 'Error'")

    # Bước 1b: Áp dụng ngưỡng sinh lý
    for col, (lower, upper) in PHYSIOLOGICAL_LIMITS.items():
        if col in df.columns:
            mask = (df[col] < lower) | (df[col] > upper)
            n_invalid = mask.sum()
            df.loc[mask, col] = np.nan
            if n_invalid > 0:
                print(f"    ✗ {col}: {n_invalid} giá trị ngoài [{lower}, {upper}] → NaN")

    print(f"    Bản ghi còn lại: {len(df)}")
    return df
