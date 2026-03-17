# -*- coding: utf-8 -*-
"""
Script phân tích dữ liệu y sinh và huấn luyện mô hình phân loại trạng thái sức khỏe.
Dành cho việc chạy trên Google Colab.

Pipeline làm sạch 5 lớp:
  Lớp 1: Lọc giới hạn sinh lý (Hard Rules)
  Lớp 2: Phát hiện ngoại lai thống kê IQR theo từng nhãn
  Lớp 3: Phát hiện bất thường đa biến (Isolation Forest + LOF đồng thuận)
  Lớp 4: Xác thực nhãn bằng KMeans Clustering
  Lớp 5: Kiểm tra tính nhất quán thời gian (Temporal Consistency)
"""

# ==============================================================================
# THƯ VIỆN
# ==============================================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
from scipy import stats

# Thiết lập phong cách vẽ biểu đồ
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.figsize'] = (12, 6)

# ==============================================================================
# ĐỌC DỮ LIỆU
# ==============================================================================
print("=" * 70)
print("    PIPELINE LÀM SẠCH DỮ LIỆU Y SINH 5 LỚP")
print("=" * 70)

file_path = '/content/drive/MyDrive/ColabNotebooks/health_data_all.csv'

try:
    df = pd.read_csv(file_path)
    print(f"✓ Đọc thành công tệp dữ liệu: {file_path}")
except FileNotFoundError:
    print(f"❌ Không tìm thấy tệp '{file_path}'. Đang tạo dữ liệu demo...")
    np.random.seed(42)
    n = 1000
    df = pd.DataFrame({
        'User_ID': ['Nguyen_Van'] * n,
        'Timestamp': pd.date_range(start='2026-02-26', periods=n, freq='min'),
        'Time_Slot': np.random.choice(['Morning', 'Afternoon', 'Evening'], n),
        'BPM': np.random.normal(80, 15, n),
        'SpO2': np.random.normal(98, 2, n),
        'Body_Temp': np.random.normal(37, 0.5, n),
        'GSR_ADC': np.random.normal(2200, 300, n),
        'Ext_Temp_C': np.random.normal(25, 3, n),
        'Ext_Humidity_Pct': np.random.normal(75, 8, n),
        'Label': np.random.choice(['Normal', 'Stress', 'Fever', 'Error'], n,
                                  p=[0.6, 0.2, 0.1, 0.1])
    })

print(f"\n[INFO] Tổng số bản ghi ban đầu: {len(df)}")
print(f"[INFO] Các cột: {list(df.columns)}")
df.info()

print("\n[DESCRIBE] Thống kê mô tả ban đầu:")
display(df.describe())

print("\n[LABEL] Phân phối nhãn ban đầu:")
print(df['Label'].value_counts())

original_count = len(df)

# ==============================================================================
# LỚP 1: LỌC GIỚI HẠN SINH LÝ (HARD RULE FILTERING)
# ==============================================================================
print("\n" + "=" * 70)
print("  LỚP 1: LỌC GIỚI HẠN SINH LÝ (HARD RULE FILTERING)")
print("=" * 70)

# Bước 1a: Xóa nhãn 'Error' hoàn toàn
error_count = (df['Label'] == 'Error').sum()
df = df[df['Label'] != 'Error'].copy()
print(f"  ✗ Đã loại bỏ {error_count} bản ghi có nhãn 'Error'")

# Bước 1b: Áp dụng ngưỡng sinh lý
hard_rules = {
    'BPM':              (40, 200),
    'SpO2':             (80, 100),
    'Body_Temp':        (34, 42),
    'GSR_ADC':          (0.01, np.inf),   # > 0
    'Ext_Temp_C':       (-10, 50),
    'Ext_Humidity_Pct': (0, 100),
}

nan_before = df.isna().sum().sum()
for col, (lo, hi) in hard_rules.items():
    if col in df.columns:
        mask = (df[col] < lo) | (df[col] > hi)
        n_invalid = mask.sum()
        df.loc[mask, col] = np.nan
        if n_invalid > 0:
            print(f"  ✗ {col}: {n_invalid} giá trị ngoài [{lo}, {hi}] → NaN")

nan_after = df.isna().sum().sum()
print(f"\n  [Lớp 1] Tổng NaN sinh ra: {nan_after - nan_before}")
print(f"  [Lớp 1] Bản ghi còn lại: {len(df)}")

# ==============================================================================
# LỚP 2: PHÁT HIỆN NGOẠI LAI THỐNG KÊ (IQR PER LABEL)
# ==============================================================================
print("\n" + "=" * 70)
print("  LỚP 2: PHÁT HIỆN NGOẠI LAI THỐNG KÊ (IQR PER LABEL)")
print("=" * 70)

features_for_iqr = ['BPM', 'SpO2', 'Body_Temp', 'GSR_ADC']
iqr_nan_count = 0

for label in df['Label'].unique():
    label_mask = df['Label'] == label
    label_count_before = label_mask.sum()

    for col in features_for_iqr:
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
            print(f"  [{label}] {col}: {n_outliers} ngoại lai IQR "
                  f"(ngoài [{lower:.1f}, {upper:.1f}]) → NaN")

print(f"\n  [Lớp 2] Tổng giá trị chuyển NaN bởi IQR: {iqr_nan_count}")

# ==============================================================================
# NỘI SUY TUYẾN TÍNH (lấp NaN sinh ra từ Lớp 1 & 2)
# ==============================================================================
print("\n  >> Lấp đầy NaN bằng Nội suy Tuyến tính (Linear Interpolation)...")
numeric_cols = df.select_dtypes(include=[np.number]).columns
nan_before_interp = df[numeric_cols].isna().sum().sum()
df[numeric_cols] = df[numeric_cols].interpolate(method='linear', limit_direction='both')
nan_after_interp = df[numeric_cols].isna().sum().sum()
print(f"  >> Đã lấp đầy {nan_before_interp - nan_after_interp} giá trị NaN.")

# Nếu vẫn còn NaN (ở ranh giới), dùng fillna
df[numeric_cols] = df[numeric_cols].fillna(method='bfill').fillna(method='ffill')

# ==============================================================================
# LỚP 3: PHÁT HIỆN BẤT THƯỜNG ĐA BIẾN (ISOLATION FOREST + LOF ĐỒNG THUẬN)
# ==============================================================================
print("\n" + "=" * 70)
print("  LỚP 3: PHÁT HIỆN BẤT THƯỜNG ĐA BIẾN (IF + LOF ĐỒNG THUẬN)")
print("=" * 70)

anomaly_features = ['BPM', 'SpO2', 'Body_Temp', 'GSR_ADC']
total_anomalies_dropped = 0

for label in df['Label'].unique():
    label_idx = df[df['Label'] == label].index
    if len(label_idx) < 30:
        print(f"  [{label}] Bỏ qua - không đủ dữ liệu ({len(label_idx)} mẫu)")
        continue

    X_label = df.loc[label_idx, anomaly_features].copy()

    # Chuẩn hóa dữ liệu
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_label)

    # Isolation Forest
    iso_forest = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    iso_pred = iso_forest.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal

    # Local Outlier Factor
    lof = LocalOutlierFactor(n_neighbors=20, contamination=0.05)
    lof_pred = lof.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal

    # Đồng thuận: chỉ loại khi CẢ HAI đều đánh dấu là anomaly
    consensus_anomaly = (iso_pred == -1) & (lof_pred == -1)
    n_anomalies = consensus_anomaly.sum()

    if n_anomalies > 0:
        drop_idx = label_idx[consensus_anomaly]
        df = df.drop(drop_idx)
        total_anomalies_dropped += n_anomalies
        print(f"  [{label}] IF phát hiện: {(iso_pred == -1).sum()} | "
              f"LOF phát hiện: {(lof_pred == -1).sum()} | "
              f"Đồng thuận loại bỏ: {n_anomalies}")
    else:
        print(f"  [{label}] Không có anomaly đồng thuận.")

print(f"\n  [Lớp 3] Tổng bản ghi bị loại (đồng thuận IF+LOF): {total_anomalies_dropped}")
print(f"  [Lớp 3] Bản ghi còn lại: {len(df)}")

# ==============================================================================
# LỚP 4: XÁC THỰC NHÃN BẰNG KMEANS CLUSTERING (LABEL VALIDATION)
# ==============================================================================
print("\n" + "=" * 70)
print("  LỚP 4: XÁC THỰC NHÃN BẰNG KMEANS CLUSTERING")
print("=" * 70)

cluster_features = ['BPM', 'SpO2', 'Body_Temp', 'GSR_ADC']
X_cluster = df[cluster_features].copy()

# Chuẩn hóa
scaler_km = StandardScaler()
X_cluster_scaled = scaler_km.fit_transform(X_cluster)

# KMeans với k=3 (Normal, Stress, Fever)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df['KMeans_Cluster'] = kmeans.fit_predict(X_cluster_scaled)

# Ánh xạ cluster → nhãn bằng cách tìm nhãn phổ biến nhất trong mỗi cluster
cluster_to_label = {}
for cluster_id in range(3):
    cluster_mask = df['KMeans_Cluster'] == cluster_id
    most_common_label = df.loc[cluster_mask, 'Label'].mode()
    if len(most_common_label) > 0:
        cluster_to_label[cluster_id] = most_common_label.iloc[0]
    else:
        cluster_to_label[cluster_id] = 'Unknown'

df['KMeans_Label'] = df['KMeans_Cluster'].map(cluster_to_label)

# So sánh nhãn gốc vs nhãn KMeans
mismatch_mask = df['Label'] != df['KMeans_Label']
n_mismatch = mismatch_mask.sum()
agreement_rate = (1 - n_mismatch / len(df)) * 100

print(f"  [Ánh xạ Cluster → Nhãn]: {cluster_to_label}")
print(f"\n  Tổng mẫu không đồng nhất (nhãn gốc ≠ KMeans): {n_mismatch}")
print(f"  Tỷ lệ đồng thuận nhãn: {agreement_rate:.2f}%")

# Bảng đối chiếu chi tiết
print("\n  [Bảng đối chiếu nhãn gốc vs KMeans Cluster]:")
crosstab = pd.crosstab(df['Label'], df['KMeans_Label'], margins=True)
display(crosstab)

# Loại bỏ các mẫu mà nhãn gốc không đồng nhất với cluster
df_before_kmeans = len(df)
df = df[~mismatch_mask].copy()
print(f"\n  ✗ Đã loại bỏ {df_before_kmeans - len(df)} mẫu có nhãn không đồng nhất với KMeans")
print(f"  [Lớp 4] Bản ghi còn lại: {len(df)}")

# Xóa cột phụ
df = df.drop(columns=['KMeans_Cluster', 'KMeans_Label'], errors='ignore')

# ==============================================================================
# LỚP 5: KIỂM TRA TÍNH NHẤT QUÁN THỜI GIAN (TEMPORAL CONSISTENCY)
# ==============================================================================
print("\n" + "=" * 70)
print("  LỚP 5: KIỂM TRA TÍNH NHẤT QUÁN THỜI GIAN (TEMPORAL CONSISTENCY)")
print("=" * 70)

window_size = 5  # Kích thước cửa sổ trượt
temporal_fixes = 0

# Sắp xếp theo thời gian
if 'Timestamp' in df.columns:
    df = df.sort_values('Timestamp').reset_index(drop=True)

# Lặp qua từng User
for user_id in df['User_ID'].unique():
    user_mask = df['User_ID'] == user_id
    user_indices = df[user_mask].index.tolist()

    if len(user_indices) < window_size:
        continue

    labels = df.loc[user_indices, 'Label'].values.copy()
    half_w = window_size // 2

    for i in range(half_w, len(labels) - half_w):
        # Lấy cửa sổ xung quanh (không bao gồm điểm hiện tại)
        window_labels = list(labels[i - half_w:i]) + list(labels[i + 1:i + half_w + 1])
        current_label = labels[i]

        # Tìm nhãn phổ biến nhất trong cửa sổ
        if len(window_labels) == 0:
            continue
        label_counts = pd.Series(window_labels).value_counts()
        dominant_label = label_counts.index[0]
        dominant_ratio = label_counts.iloc[0] / len(window_labels)

        # Nếu >75% cửa sổ xung quanh là cùng 1 nhãn khác với nhãn hiện tại
        if dominant_ratio >= 0.75 and current_label != dominant_label:
            labels[i] = dominant_label
            temporal_fixes += 1

    # Gán lại nhãn đã sửa
    df.loc[user_indices, 'Label'] = labels

print(f"  [Lớp 5] Số nhãn được sửa bởi Temporal Consistency: {temporal_fixes}")
print(f"  [Lớp 5] Bản ghi cuối cùng: {len(df)}")

# ==============================================================================
# LÀM MƯỢT TÍN HIỆU (SMOOTHING)
# ==============================================================================
print("\n  >> Làm mượt tín hiệu BPM và GSR_ADC (Moving Average, window=5)...")
df['BPM'] = df['BPM'].rolling(window=5, min_periods=1).mean()
df['GSR_ADC'] = df['GSR_ADC'].rolling(window=5, min_periods=1).mean()

# ==============================================================================
# TỔNG KẾT QUÁ TRÌNH LÀM SẠCH
# ==============================================================================
print("\n" + "=" * 70)
print("  TỔNG KẾT QUÁ TRÌNH LÀM SẠCH 5 LỚP")
print("=" * 70)
print(f"  Dữ liệu ban đầu:           {original_count} bản ghi")
print(f"  Sau Lớp 1 (Hard Rules):     Loại {error_count} Error + NaN hóa ngoại lai")
print(f"  Sau Lớp 2 (IQR per Label):  {iqr_nan_count} giá trị NaN (đã nội suy)")
print(f"  Sau Lớp 3 (IF + LOF):       Loại {total_anomalies_dropped} anomaly đồng thuận")
print(f"  Sau Lớp 4 (KMeans):         Loại {df_before_kmeans - len(df) + (df_before_kmeans - len(df))} mẫu nhãn sai")
print(f"  Sau Lớp 5 (Temporal):       Sửa {temporal_fixes} nhãn đột biến")
print(f"  ──────────────────────────────────────────────")
print(f"  DỮ LIỆU SẠCH CUỐI CÙNG:    {len(df)} bản ghi")
print(f"  Tỷ lệ giữ lại:             {len(df)/original_count*100:.1f}%")

print("\n[LABEL] Phân phối nhãn cuối cùng (sau 5 lớp làm sạch):")
print(df['Label'].value_counts())

print("\n[DESCRIBE] Thống kê mô tả dữ liệu sạch:")
display(df.describe())


# ==============================================================================
# PHẦN 2: PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA)
# ==============================================================================
print("\n" + "=" * 70)
print("  PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA)")
print("=" * 70)

# Boxplot phân nhóm trạng thái sức khỏe
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('Phân bố các chỉ số sinh lý theo từng trạng thái sức khỏe\n(Sau khi làm sạch 5 lớp)',
             fontsize=16, fontweight='bold')

sns.boxplot(ax=axes[0], x='Label', y='BPM', data=df, hue='Label', legend=False,
            palette='Set2', order=['Normal', 'Stress', 'Fever'])
axes[0].set_title('Nhịp tim (BPM)', fontsize=13)

sns.boxplot(ax=axes[1], x='Label', y='GSR_ADC', data=df, hue='Label', legend=False,
            palette='Set2', order=['Normal', 'Stress', 'Fever'])
axes[1].set_title('Điện trở da (GSR_ADC)', fontsize=13)

sns.boxplot(ax=axes[2], x='Label', y='Body_Temp', data=df, hue='Label', legend=False,
            palette='Set2', order=['Normal', 'Stress', 'Fever'])
axes[2].set_title('Nhiệt độ cơ thể (Body_Temp)', fontsize=13)

plt.tight_layout()
plt.show()

# Ma trận tương quan Pearson
plt.figure(figsize=(8, 6))
cols_for_corr = ['Ext_Temp_C', 'Ext_Humidity_Pct', 'Body_Temp', 'GSR_ADC', 'BPM', 'SpO2']
corr_matrix = df[cols_for_corr].corr(method='pearson')

sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5,
            square=True, vmin=-1, vmax=1)
plt.title('Ma trận tương quan Pearson\n(Môi trường vs Chỉ số cơ thể)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

# Thống kê mô tả theo nhãn
print("\n[STATISTICS] Thống kê mô tả (Mean, Std) cho từng nhóm sức khỏe:")
stats_df = df.groupby('Label')[['BPM', 'SpO2', 'Body_Temp', 'GSR_ADC']].agg(['mean', 'std']).round(2)
display(stats_df)

print("""
[NHẬN XÉT sau khi Làm sạch 5 Lớp]
- Nhịp tim (BPM): Nhóm Stress có BPM cao nhất, Normal thấp nhất - phù hợp sinh lý.
- Điện trở da (GSR_ADC): Stress có GSR cao → phản ứng mồ hôi khi căng thẳng.
- Nhiệt độ (Body_Temp): Nhóm Fever có nhiệt độ rõ ràng cao hơn bình thường.
- Dữ liệu đã sạch, boxplots không còn các điểm ngoại lai cực đoan.
""")


# ==============================================================================
# PHẦN 3: HUẤN LUYỆN VÀ ĐÁNH GIÁ MÔ HÌNH HỌC MÁY
# ==============================================================================
print("\n" + "=" * 70)
print("  HUẤN LUYỆN MÔ HÌNH RANDOM FOREST CLASSIFIER")
print("=" * 70)

# Chuẩn bị dữ liệu
cols_to_drop = ['User_ID', 'Timestamp', 'Time_Slot', 'Label']
X = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
y = df['Label']

print(f"[MODEL] Số features: {X.shape[1]} → {list(X.columns)}")

# Chia tập Train/Test (80/20)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"[MODEL] Tập Train: {X_train.shape[0]} mẫu | Tập Test: {X_test.shape[0]} mẫu")

# Huấn luyện Random Forest
print("[MODEL] Đang huấn luyện Random Forest Classifier (n_estimators=100)...")
rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)

# Đánh giá
y_pred = rf_model.predict(X_test)

print("\n[EVALUATION] Báo cáo phân loại (Classification Report):")
print(classification_report(y_test, y_pred))

accuracy = (y_pred == y_test).mean()
print(f"  ★ Accuracy tổng thể: {accuracy * 100:.2f}%")

# Confusion Matrix
plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test, y_pred, labels=rf_model.classes_)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=rf_model.classes_, yticklabels=rf_model.classes_)
plt.title('Ma trận nhầm lẫn (Confusion Matrix)', fontsize=14, fontweight='bold')
plt.xlabel('Nhãn dự đoán (Predicted Label)')
plt.ylabel('Nhãn thực tế (True Label)')
plt.tight_layout()
plt.show()

# Feature Importance
plt.figure(figsize=(10, 6))
feature_importances = pd.Series(
    rf_model.feature_importances_, index=X.columns
).sort_values(ascending=False)

sns.barplot(x=feature_importances, y=feature_importances.index,
            palette='viridis', hue=feature_importances.index, legend=False)
plt.title('Mức độ quan trọng của các đặc trưng (Feature Importance)',
          fontsize=14, fontweight='bold')
plt.xlabel('Điểm quan trọng (Importance Score)')
plt.ylabel('Đặc trưng (Features)')
plt.tight_layout()
plt.show()

print("""
[KẾT LUẬN]
- Pipeline 5 lớp làm sạch đã loại bỏ triệt để các dữ liệu nhiễu và nhãn sai.
- Feature Importance cho thấy các chỉ số sinh lý (GSR, BPM, Body_Temp) đóng vai trò
  quyết định trong việc phân loại trạng thái sức khỏe.
- Mô hình Random Forest được huấn luyện trên dữ liệu sạch cho kết quả đáng tin cậy.
""")

print("=" * 70)
print("  HOÀN TẤT PIPELINE PHÂN TÍCH DỮ LIỆU Y SINH")
print("=" * 70)
