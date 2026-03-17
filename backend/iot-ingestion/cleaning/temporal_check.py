# -*- coding: utf-8 -*-
"""
Lớp 5: Kiểm tra tính nhất quán thời gian (Temporal Consistency).

Nguyên lý:
  - Dùng cửa sổ trượt (sliding window) kiểm tra nhãn xung quanh mỗi điểm.
  - Nếu >75% các nhãn xung quanh là cùng 1 nhãn khác với nhãn hiện tại
    → nhãn hiện tại là "đột biến" → sửa theo nhãn đa số.
  - Cuối cùng áp dụng smoothing (Moving Average) cho BPM và GSR_ADC.

Tham khảo: Health_Analysis.py - Lớp 5
"""

import pandas as pd


# Kích thước cửa sổ trượt
WINDOW_SIZE = 5

# Ngưỡng tỷ lệ đa số để sửa nhãn đột biến
DOMINANCE_THRESHOLD = 0.75

# Kích thước cửa sổ cho smoothing
SMOOTHING_WINDOW = 5


def apply_temporal_check(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kiểm tra và sửa nhãn đột biến theo thời gian + làm mượt tín hiệu.

    Args:
        df: DataFrame đã qua Lớp 4

    Returns:
        DataFrame với nhãn đã sửa và tín hiệu đã làm mượt
    """
    print("  [Lớp 5] Đang kiểm tra tính nhất quán thời gian...")

    temporal_fixes = 0

    # Sắp xếp theo thời gian nếu có cột timestamp
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)

    # Kiểm tra nhãn theo cửa sổ trượt cho từng user
    if "label" in df.columns and "user_id" in df.columns:
        half_w = WINDOW_SIZE // 2

        for user_id in df["user_id"].unique():
            user_mask = df["user_id"] == user_id
            user_indices = df[user_mask].index.tolist()

            if len(user_indices) < WINDOW_SIZE:
                continue

            labels = df.loc[user_indices, "label"].values.copy()

            for i in range(half_w, len(labels) - half_w):
                # Lấy nhãn trong cửa sổ (không bao gồm điểm hiện tại)
                window_labels = list(labels[i - half_w:i]) + list(labels[i + 1:i + half_w + 1])
                current_label = labels[i]

                if not window_labels:
                    continue

                # Tìm nhãn đa số
                label_counts = pd.Series(window_labels).value_counts()
                dominant_label = label_counts.index[0]
                dominant_ratio = label_counts.iloc[0] / len(window_labels)

                # Sửa nhãn đột biến nếu vượt ngưỡng
                if dominant_ratio >= DOMINANCE_THRESHOLD and current_label != dominant_label:
                    labels[i] = dominant_label
                    temporal_fixes += 1

            # Gán lại nhãn đã sửa
            df.loc[user_indices, "label"] = labels

    print(f"    Số nhãn được sửa: {temporal_fixes}")

    # Làm mượt tín hiệu (Moving Average)
    if "bpm" in df.columns:
        df["bpm"] = df["bpm"].rolling(window=SMOOTHING_WINDOW, min_periods=1).mean()
    if "gsr_adc" in df.columns:
        df["gsr_adc"] = df["gsr_adc"].rolling(window=SMOOTHING_WINDOW, min_periods=1).mean()

    print(f"    ✓ Đã làm mượt tín hiệu (Moving Average, window={SMOOTHING_WINDOW})")
    return df
