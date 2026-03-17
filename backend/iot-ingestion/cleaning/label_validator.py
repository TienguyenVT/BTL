# -*- coding: utf-8 -*-
"""
Lớp 4: Xác thực nhãn bằng KMeans Clustering (Label Validation).

Nguyên lý:
  - Dùng KMeans phân cụm dữ liệu thành k nhóm (k = số nhãn).
  - Ánh xạ mỗi cluster → nhãn phổ biến nhất trong cluster.
  - Nếu nhãn gốc ≠ nhãn cluster → bản ghi có nhãn sai → loại bỏ.

Tham khảo: Health_Analysis.py - Lớp 4
"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# Số cluster = số loại nhãn (Normal, Stress, Fever)
N_CLUSTERS = 3

# Các trường dùng cho clustering
CLUSTER_FEATURES = ["bpm", "spo2", "body_temp", "gsr_adc"]


def apply_label_validation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Xác thực nhãn bằng KMeans clustering.
    Loại bỏ bản ghi có nhãn không đồng nhất với cluster.

    Args:
        df: DataFrame đã qua Lớp 3

    Returns:
        DataFrame đã loại bỏ bản ghi có nhãn sai
    """
    print("  [Lớp 4] Đang xác thực nhãn bằng KMeans Clustering...")

    if "label" not in df.columns or len(df) < N_CLUSTERS * 10:
        print("    ⚠ Bỏ qua - không đủ dữ liệu hoặc không có nhãn")
        return df

    X_cluster = df[CLUSTER_FEATURES].copy()

    # Chuẩn hóa trước khi cluster
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_cluster)

    # Chạy KMeans
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    df["_kmeans_cluster"] = kmeans.fit_predict(X_scaled)

    # Ánh xạ cluster → nhãn phổ biến nhất
    cluster_to_label = {}
    for cluster_id in range(N_CLUSTERS):
        cluster_mask = df["_kmeans_cluster"] == cluster_id
        most_common = df.loc[cluster_mask, "label"].mode()
        cluster_to_label[cluster_id] = most_common.iloc[0] if len(most_common) > 0 else "Unknown"

    df["_kmeans_label"] = df["_kmeans_cluster"].map(cluster_to_label)

    # Loại bỏ bản ghi có nhãn không khớp cluster
    mismatch_mask = df["label"] != df["_kmeans_label"]
    n_mismatch = mismatch_mask.sum()
    agreement_rate = (1 - n_mismatch / len(df)) * 100

    df_before = len(df)
    df = df[~mismatch_mask].copy()

    # Xóa cột tạm
    df = df.drop(columns=["_kmeans_cluster", "_kmeans_label"], errors="ignore")

    print(f"    Tỷ lệ đồng thuận nhãn: {agreement_rate:.1f}%")
    print(f"    Loại bỏ {df_before - len(df)} mẫu nhãn sai | Còn lại: {len(df)}")
    return df
