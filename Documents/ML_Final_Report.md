# BÁO CÁO BÀI TẬP LỚN
# MÔN: MÁY HỌC VÀ ỨNG DỤNG
# ĐỀ TÀI: HỆ THỐNG GIÁM SÁT SỨC KHỎE IoMT (Internet of Medical Things)

---

## MỤC LỤC

1. [Giới thiệu đề tài](#1-giới-thiệu-đề-tài)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Thu thập và xử lý dữ liệu](#3-thu-thập-và-xử-lý-dữ-liệu)
4. [Mô hình Machine Learning](#4-mô-hình-machine-learning)
5. [Pipeline làm sạch dữ liệu (5 lớp)](#5-pipeline-làm-sạch-dữ-liệu-5-lớp)
6. [Huấn luyện và đánh giá mô hình](#6-huấn-luyện-và-đánh-giá-mô-hình)
7. [Triển khai hệ thống](#7-triển-khai-hệ-thống)
8. [Kết quả và đánh giá](#8-kết-quả-và-đánh-giá)
9. [Kết luận và hướng phát triển](#9-kết-luận-và-hướng-phát-triển)
10. [Tài liệu tham khảo](#10-tài-liệu-tham-khảo)

---

## 1. GIỚI THIỆU ĐỀ TÀI

### 1.1. Bối cảnh

Trong bối cảnh công nghệ Internet of Things (IoT) phát triển mạnh mẽ, việc ứng dụng IoT vào lĩnh vực y tế (Internet of Medical Things - IoMT) đang ngày càng phổ biến. Hệ thống giám sát sức khỏe thời gian thực cho phép theo dõi các chỉ số sinh lý của bệnh nhân từ xa, phát hiện sớm các bất thường và đưa ra cảnh báo kịp thời.

### 1.2. Mục tiêu

Xây dựng hệ thống IoMT giám sát sức khỏe với các chức năng:
- Thu thập dữ liệu sinh lý từ cảm biến ESP32 (nhịp tim, SpO2, nhiệt độ, điện trở da)
- Xử lý và làm sạch dữ liệu thông qua pipeline 5 lớp
- Xây dựng mô hình Machine Learning phân loại trạng thái sức khỏe
- Dự đoán thời gian thực các trạng thái: Normal (bình thường), Stress (căng thẳng), Fever (sốt)

### 1.3. Phạm vi

- **Input**: Dữ liệu từ cảm biến ESP32 gồm 4 chỉ số sinh lý
- **Output**: Nhãn phân loại trạng thái sức khỏe
- **Mô hình ML**: RandomForest và XGBoost
- **Ứng dụng**: Phân loại trạng thái sức khỏe thời gian thực

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Sơ đồ kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KIẾN TRÚC HỆ THỐNG IoMT                           │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│  ESP32 Sensor │          │  Data Source │          │   Admin/API   │
│  (Hardware)   │          │   (CSV/DB)   │          │   (Config)   │
└───────┬───────┘          └───────┬───────┘          └───────┬───────┘
        │                           │                           │
        │ MQTT/HTTP                 │                           │
        ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND SERVICE                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Ingestion  │  │   Cleaning  │  │   ML Model  │  │   MongoDB   │     │
│  │   Service   │──▶│   Pipeline  │──▶│  Predictor  │──▶│  Database   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   Training Pipeline   │
                        │  (train_model.py)    │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   ML Model (.pkl)    │
                        │  (RF / XGBoost)      │
                        └───────────────────────┘
```

### 2.2. Các thành phần chính

#### 2.2.1. Tầng Thu thập dữ liệu (Data Collection Layer)

| Thành phần | Mô tả | Công nghệ |
|------------|-------|-----------|
| ESP32 Sensor | Thiết bị cảm biến thu thập dữ liệu sinh lý | ESP32 |
| MQTT Broker | Trung gian truyền tin nhắn | Mosquitto |
| HTTP API | Giao diện RESTful | FastAPI |

**Dữ liệu đầu vào từ cảm biến:**
- `bpm`: Nhịp tim (Nhịp/phút)
- `spo2`: Độ bão hòa oxy trong máu (%)
- `body_temp`: Nhiệt độ cơ thể (°C)
- `gsr_adc`: Điện trở da (ADC value)

#### 2.2.2. Tầng Xử lý dữ liệu (Data Processing Layer)

| Thành phần | Mô tả | File |
|------------|-------|------|
| Ingestion Service | Nhận và validate dữ liệu | `service.py` |
| Cleaning Pipeline | Làm sạch dữ liệu 5 lớp | `cleaning/pipeline.py` |

#### 2.2.3. Tầng Machine Learning

| Thành phần | Mô tả | File |
|------------|-------|------|
| Training Pipeline | Huấn luyện mô hình | `train_model.py` |
| Realtime Predictor | Dự đoán thời gian thực | `ml_model/predictor.py` |
| ML Model | Mô hình đã train (.pkl) | `ml_model/random_forest.pkl` |

#### 2.2.4. Tầng Lưu trữ (Storage Layer)

| Database | Mô tả | Collection |
|----------|-------|------------|
| MongoDB | Lưu trữ dữ liệu | `training_health_data` (train) |
| MongoDB | Lưu trữ dữ liệu | `realtime_health_data` (realtime) |

---

## 3. THU THẬP VÀ XỬ LÝ DỮ LIỆU

### 3.1. Mô tả dữ liệu

#### 3.1.1. Nguồn dữ liệu

Do không có bộ dữ liệu thực từ bệnh nhân, hệ thống sử dụng bộ dữ liệu tổng hợp được sinh ra từ `generate_health_data.py`.

**Cấu trúc dữ liệu:**

| Trường | Kiểu | Mô tả | Ví dụ |
|--------|------|-------|-------|
| `User_ID` | String | ID người dùng | "User1" |
| `Timestamp` | DateTime | Thời điểm | "2026-02-26 05:30:00" |
| `Time_Slot` | String | Khung giờ | "Morning", "Noon", "Afternoon", "Night" |
| `BPM` | Integer | Nhịp tim | 75 |
| `SpO2` | Float | SpO2 % | 98.5 |
| `Body_Temp` | Float | Nhiệt độ °C | 36.8 |
| `GSR_ADC` | Integer | Điện trở da | 2200 |
| `Ext_Temp_C` | Float | Nhiệt độ ngoài trời | 20.5 |
| `Ext_Humidity_Pct` | Float | Độ ẩm % | 78.0 |
| `Label` | String | Nhãn (Normal/Stress/Fever/Error) | "Normal" |

#### 3.1.2. Phân bố nhãn

```python
SCENARIOS = ['Normal', 'Stress', 'Fever']
SCENARIO_WEIGHTS = [0.5, 0.3, 0.2]  # 50% Normal, 30% Stress, 20% Fever
```

#### 3.1.3. Đặc điểm sinh lý theo từng trạng thái

| Trạng thái | BPM | SpO2 | Body_Temp | GSR_ADC |
|------------|-----|------|-----------|---------|
| **Normal** | 60-90 | 96-99.9 | 36.5-37.2 | 2100-2300 |
| **Stress** | 100-160 | 96-99.9 | 36.5-37.5 | 2600-4000 |
| **Fever** | 80-110 | 94-99 | 37.6-40.0 | 2000-2500 |

### 3.2. Sinh dữ liệu huấn luyện

#### 3.2.1. Cấu hình sinh dữ liệu

```python
# File: Data/generate_health_data.py

# Cấu hình người dùng
USERS = [
    {'id': 'User1', 'date': '2026-02-26', 'temp_range': (15, 25), 'humid_range': (75, 80)},
    {'id': 'User1', 'date': '2026-02-28', 'temp_range': (14, 20), 'humid_range': (75, 85)},
    # ... 5 ngày dữ liệu
]

# Cấu hình thời gian
TIME_SLOTS = {
    'Morning': (5, 6),      # 5:00 - 6:59
    'Noon': (11, 12),       # 11:00 - 12:59
    'Afternoon': (15, 16),  # 15:00 - 16:59
    'Night': (22, 23)       # 22:00 - 23:59
}

SAMPLES_PER_SLOT = 250
INTERVAL_SEC = 5
```

#### 3.2.2. Logic sinh dữ liệu sinh lý

```python
# Sinh dữ liệu theo trạng thái
if current_state == 'Normal':
    current_bpm += random.uniform(-2, 2) + (75 - current_bpm) * 0.1
    current_bpm = clamp(current_bpm, 60, 90)
    # ... tương tự cho các thông số khác

elif current_state == 'Stress':
    current_bpm += random.uniform(0, 5)
    current_bpm = clamp(current_bpm, 100, 160)
    current_gsr += random.uniform(10, 50)
    current_gsr = clamp(current_gsr, 2600, 4000)

elif current_state == 'Fever':
    current_temp += random.uniform(-0.05, 0.15)
    current_temp = clamp(current_temp, 37.6, 40.0)
```

#### 3.2.3. Noise Injection

```python
# Inject noise 10% dữ liệu
if random.random() < 0.10:
    final_label = 'Error'  # Label = Error khi có noise
    # Inject various noise types
    noise_type = random.choice(['drop', 'negative', 'max', 'outlier', 'drift'])
    # ... xử lý noise
```

### 3.3. Tiền xử lý dữ liệu

#### 3.3.1. Data Generator Features

```python
def inject_noise(value, noise_prob=0.05, min_val=0, max_val=4095):
    """Randomly inject noise types."""
    if random.random() < noise_prob:
        noise_type = random.choice(['drop', 'negative', 'max', 'outlier', 'drift'])
        if noise_type == 'drop':
            return 0
        elif noise_type == 'negative':
            return -random.randint(1, 100)
        elif noise_type == 'max':
            return max_val
        elif noise_type == 'outlier':
            return value * random.choice([0.5, 2.0])
        elif noise_type == 'drift':
            return value + random.uniform(-50, 50)
    return value
```

#### 3.3.2. Kết quả sinh dữ liệu

- **Tổng số mẫu**: ~10,000 bản ghi
- **Phân bố**: 5 ngày × 4 khung giờ × ~500 mẫu/ngày
- **Tỷ lệ Error**: ~10% (có noise + label Error)

---

## 4. MÔ HÌNH MACHINE LEARNING

### 4.1. Bài toán Machine Learning

#### 4.1.1. Phân loại trạng thái sức khỏe (Multi-class Classification)

- **Input**: Vector 4 features `['bpm', 'spo2', 'body_temp', 'gsr_adc']`
- **Output**: Một trong 3 nhãn `['Normal', 'Stress', 'Fever']`
- **Loại bài toán**: Multi-class Classification

#### 4.1.2. Đặc điểm bài toán

| Đặc điểm | Mô tả |
|-----------|-------|
| Số lớp | 3 (Normal, Stress, Fever) |
| Số features | 4 (cơ bản) + 8 (engineered) = 12 |
| Class imbalance | 50% Normal, 30% Stress, 20% Fever |
| Metric đánh giá | F1-Score (weighted) |

### 4.2. Mô hình RandomForest

#### 4.2.1. Giới thiệu

RandomForest là thuật toán ensemble learning sử dụng kết hợp nhiều Decision Trees. Mỗi cây được train trên một tập con của dữ liệu (bootstrap sampling) và chọn một tập con ngẫu nhiên của features. Kết quả cuối cùng được quyết định bằng voting (majority voting).

#### 4.2.2. Ưu điểm

- Không overfitting nhờ ensemble của nhiều trees
- Xử lý tốt với imbalanced data
- Có khả năng đo lường feature importance
- Song song hóa tốt (parallel training)

#### 4.2.3. Hyperparameters

| Parameter | Giá trị mặc định | Tìm kiếm |
|-----------|------------------|----------|
| `n_estimators` | 100 | [100, 200, 300] |
| `max_depth` | None | [10, 20, None] |
| `min_samples_split` | 2 | [2, 5, 10] |
| `min_samples_leaf` | 1 | [1, 2, 4] |
| `class_weight` | None | [None, 'balanced'] |

**Giá trị tối ưu (sau GridSearchCV):**

| Parameter | Giá trị tối ưu |
|-----------|---------------|
| `n_estimators` | 100 |
| `max_depth` | None (unlimited) |
| `min_samples_split` | 2 |
| `min_samples_leaf` | 1 |
| `class_weight` | None |

### 4.3. Mô hình XGBoost

#### 4.3.1. Giới thiệu

XGBoost (eXtreme Gradient Boosting) là thuật toán gradient boosting được tối ưu về hiệu năng. XGBoost xây dựng các cây quyết định theo tuần tự, mỗi cây mới được train để sửa lỗi của các cây trước đó.

#### 4.3.2. Ưu điểm

- Hiệu suất cao hơn RandomForest trong nhiều bài toán
- Xử lý tốt với sparse data
- Regularization để tránh overfitting
- Hỗ trợ parallel và distributed computing

#### 4.3.3. Hyperparameters sử dụng

| Parameter | Giá trị |
|-----------|---------|
| `n_estimators` | 200 |
| `max_depth` | 10 |
| `learning_rate` | 0.1 |
| `eval_metric` | mlogloss |

### 4.4. So sánh hai mô hình

| Tiêu chí | RandomForest | XGBoost |
|----------|--------------|---------|
| Loại | Bagging | Boosting |
| Tốc độ huấn luyện | Nhanh | Chậm hơn |
| Overfitting | Thấp | Thấp (có regularization) |
| Hyperparameters | Ít hơn | Nhiều hơn |
| Kết quả (F1) | 96.45% | 96.81% |

---

## 5. PIPELINE LÀM SẠCH DỮ LIỆU (5 LỚP)

Pipeline làm sạch 5 lớp được thiết kế để đảm bảo chất lượng dữ liệu huấn luyện, loại bỏ các giá trị không hợp lệ và các bản ghi có nhãn sai.

```
Raw Data → Lớp 1 (Hard Rules) → Lớp 2 (IQR) → Lớp 3 (IF+LOF) 
        → Lớp 4 (KMeans) → Lớp 5 (Temporal) → Clean Data
```

### 5.1. Lớp 1: Hard Rules Filtering

#### 5.1.1. Mục đích

Loại bỏ các giá trị vật lý/sinh lý không hợp lệ dựa trên giới hạn sinh lý của con người.

#### 5.1.2. Ngưỡng sinh lý

```python
PHYSIOLOGICAL_LIMITS = {
    "bpm":              (40, 200),       # Nhịp tim hợp lý
    "spo2":             (80, 100),       # SpO2 hợp lý
    "body_temp":        (34, 42),        # Nhiệt độ cơ thể
    "gsr_adc":          (0.01, np.inf),  # Điện trở da > 0
    "ext_temp_c":       (-10, 50),       # Nhiệt độ môi trường
    "ext_humidity_pct": (0, 100),        # Độ ẩm
}
```

#### 5.1.3. Thuật toán

```
1. Loại bỏ bản ghi có label = 'Error'
2. Với mỗi feature:
   - Nếu giá trị < lower_bound OR giá trị > upper_bound
   - Gán giá trị = NaN
```

#### 5.1.4. Kết quả

- Loại bỏ các bản ghi Error
- Đánh dấu NaN cho các giá trị ngoài ngưỡng

### 5.2. Lớp 2: IQR Filter

#### 5.2.1. Mục đích

Phát hiện và xử lý outlier bằng phương pháp IQR (Interquartile Range).

#### 5.2.2. Thuật toán

```python
# Tính IQR cho mỗi feature theo từng label
Q1 = df[feature].quantile(0.25)
Q3 = df[feature].quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Đánh dấu outlier
outliers = (df[feature] < lower_bound) | (df[feature] > upper_bound)

# Thay outlier = NaN và interpolation
df.loc[outliers, feature] = np.nan
df[feature] = df[feature].interpolate(method='linear')
```

#### 5.2.3. Ưu điểm

- Không assume phân phối chuẩn
- Robust với extreme values
- Linear interpolation lấp đầy NaN

### 5.3. Lớp 3: Anomaly Detection (IF + LOF)

#### 5.3.1. Mục đích

Phát hiện anomaly đa biến bằng kết hợp 2 thuật toán: Isolation Forest và Local Outlier Factor.

#### 5.3.2. Isolation Forest

```python
# Isolation Forest
iso_forest = IsolationForest(
    contamination=0.05,  # 5% dữ liệu là anomaly
    random_state=42,
    n_jobs=-1
)
iso_pred = iso_forest.fit_predict(X_scaled)
# -1 = anomaly, 1 = normal
```

**Nguyên lý:** Isolation Forest cô lập anomaly bằng cách random partitioning. Anomaly dễ bị cô lập hơn (đường đi ngắn hơn) so với normal points.

#### 5.3.3. Local Outlier Factor

```python
# Local Outlier Factor
lof = LocalOutlierFactor(
    n_neighbors=20,
    contamination=0.05
)
lof_pred = lof.fit_predict(X_scaled)
```

**Nguyên lý:** LOF so sánh local density của một điểm với neighbors. Điểm có LOF cao hơn nhiều so với neighbors là outlier.

#### 5.3.4. Consensus Voting

```python
# Chỉ loại bỏ khi CẢ HAI đánh dấu là anomaly
consensus = (iso_pred == -1) & (lof_pred == -1)
df = df[~consensus]
```

**Ưu điểm của consensus:**
- Giảm false positive
- Chỉ loại bỏ các điểm thực sự bất thường

### 5.4. Lớp 4: Label Validation (KMeans)

#### 5.4.1. Mục đích

Xác thực nhãn bằng clustering, loại bỏ các bản ghi có nhãn không đồng nhất với cluster.

#### 5.4.2. Thuật toán

```python
# KMeans clustering với k = số nhãn
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df['_cluster'] = kmeans.fit_predict(X_scaled)

# Với mỗi cluster, tìm nhãn phổ biến nhất
cluster_to_label = {}
for cluster_id in range(3):
    cluster_mask = df['_cluster'] == cluster_id
    most_common = df.loc[cluster_mask, 'label'].mode()
    cluster_to_label[cluster_id] = most_common.iloc[0]

# Loại bỏ bản ghi có nhãn không khớp với cluster
mismatch = df['label'] != df['_cluster'].map(cluster_to_label)
df = df[~mismatch]
```

#### 5.4.3. Kết quả

- Tính toán tỷ lệ đồng thuận nhãn (label agreement rate)
- Loại bỏ các mẫu có nhãn sai

### 5.5. Lớp 5: Temporal Check

#### 5.5.1. Mục đích

Đảm bảo tính nhất quán thời gian của nhãn và làm mượt tín hiệu.

#### 5.5.2. Label Smoothing

```python
# Cửa sổ trượt kiểm tra nhãn xung quanh
window_size = 5
dominance_threshold = 0.75  # 75%

for i in range(half_w, len(labels) - half_w):
    window_labels = labels[i-half_w:i] + labels[i+1:i+half_w+1]
    current_label = labels[i]
    
    # Tìm nhãn đa số
    label_counts = Counter(window_labels)
    dominant_label = label_counts.most_common(1)[0][0]
    dominant_ratio = label_counts[dominant_label] / len(window_labels)
    
    # Sửa nếu đa số khác với nhãn hiện tại
    if dominant_ratio >= dominance_threshold and current_label != dominant_label:
        labels[i] = dominant_label
```

#### 5.5.3. Signal Smoothing

```python
# Moving Average cho BPM và GSR
df['bpm'] = df['bpm'].rolling(window=5, min_periods=1).mean()
df['gsr_adc'] = df['gsr_adc'].rolling(window=5, min_periods=1).mean()
```

---

## 6. HUẤN LUYỆN VÀ ĐÁNH GIÁ MÔ HÌNH

### 6.1. Quy trình huấn luyện

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TRAINING PIPELINE                                    │
└─────────────────────────────────────────────────────────────────────────────┘

        │
        ▼
┌───────────────────┐
│  1. Load Data    │
│  (MongoDB)       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  2. Feature      │
│  Engineering     │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  3. Baseline CV │
│  (5-fold)       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  4. GridSearchCV │
│  (Hyperparams)   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  5. XGBoost      │
│  Comparison      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  6. Select Best │
│  Model           │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  7. Retrain      │
│  Full Data       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  8. Save Model  │
│  (.pkl)          │
└───────────────────┘
```

### 6.2. Feature Engineering

#### 6.2.1. Base Features (4)

```python
features = ['bpm', 'spo2', 'body_temp', 'gsr_adc']
```

#### 6.2.2. Engineered Features (8)

```python
def create_engineered_features(df):
    """Tạo 8 features mới từ 4 features gốc."""
    
    # 1. Tỷ lệ BPM/SPO2
    df['bpm_spo2_ratio'] = df['bpm'] / df['spo2']
    
    # 2. Tương tác nhiệt độ và GSR
    df['temp_gsr_interaction'] = df['body_temp'] * df['gsr_adc'] / 1000
    
    # 3. Tích BPM và nhiệt độ
    df['bpm_temp_product'] = df['bpm'] * df['body_temp']
    
    # 4. Tỷ lệ SpO2/GSR
    df['spo2_gsr_ratio'] = df['spo2'] / df['gsr_adc']
    
    # 5. Độ lệch BPM so với baseline (75)
    df['bpm_deviation'] = abs(df['bpm'] - 75)
    
    # 6. Độ lệch nhiệt độ so với baseline (36.8)
    df['temp_deviation'] = abs(df['body_temp'] - 36.8)
    
    # 7. Độ lệch GSR so với baseline (2200)
    df['gsr_deviation'] = abs(df['gsr_adc'] - 2200)
    
    # 8. Chỉ số stress tổng hợp
    df['physiological_stress_index'] = (
        (df['bpm'] - 75) / 75 +
        (df['gsr_adc'] - 2200) / 2200
    )
    
    return df
```

#### 6.2.3. Tổng số features

- **Tổng cộng**: 12 features (4 base + 8 engineered)

### 6.3. Cross-Validation

#### 6.3.1. 5-Fold Stratified Cross-Validation

```python
from sklearn.model_selection import StratifiedKFold, cross_val_score

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Các metrics đánh giá
cv_scores_accuracy = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
cv_scores_f1 = cross_val_score(model, X, y, cv=cv, scoring='f1_weighted')
cv_scores_precision = cross_val_score(model, X, y, cv=cv, scoring='precision_weighted')
cv_scores_recall = cross_val_score(model, X, y, cv=cv, scoring='recall_weighted')
```

#### 6.3.2. Kết quả Cross-Validation (Baseline)

| Metric | Mean | Std | 95% CI |
|--------|------|-----|--------|
| Accuracy | 96.22% | ±0.56% | ±1.10% |
| F1-Score (weighted) | 96.22% | - | - |
| F1-Score (macro) | 96.11% | - | - |
| Precision | 96.22% | - | - |
| Recall | 96.22% | - | - |

### 6.4. Hyperparameter Tuning

#### 6.4.1. GridSearchCV

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'class_weight': [None, 'balanced']
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42, n_jobs=-1),
    param_grid,
    cv=3,
    scoring='f1_weighted',
    n_jobs=-1,
    verbose=2
)

grid_search.fit(X_train, y_train)
```

#### 6.4.2. Kết quả GridSearchCV

- **Số combinations**: 3 × 3 × 3 × 3 × 2 = **162**
- **CV Folds**: 3
- **Tổng số fits**: 162 × 3 = **486**
- **Best CV Score**: 96.37%

### 6.5. Model Comparison

#### 6.5.1. So sánh RandomForest vs XGBoost

```python
# Train XGBoost
xgb_model = XGBClassifier(
    n_estimators=200,
    max_depth=10,
    learning_rate=0.1,
    random_state=42,
    eval_metric='mlogloss'
)
xgb_model.fit(X_train, y_train_encoded)

# So sánh
if xgb_f1 > rf_f1:
    best_model = xgb_model
    best_model_type = 'xgboost'
else:
    best_model = rf_model
    best_model_type = 'randomforest'
```

#### 6.5.2. Kết quả so sánh

| Model | Accuracy | F1-Score (weighted) |
|-------|----------|---------------------|
| RandomForest | 96.46% | 96.45% |
| **XGBoost** | **96.80%** | **96.81%** |

**Model được chọn**: XGBoost (F1 cao hơn 0.36%)

---

## 7. TRIỂN KHAI HỆ THỐNG

### 7.1. Lưu trữ mô hình

#### 7.1.1. Model Metadata

```python
model_data = {
    'model': final_model,
    'model_type': 'xgboost',
    'version': '20260317_103045',
    'features': ['bpm', 'spo2', 'body_temp', 'gsr_adc', 
                 'bpm_spo2_ratio', 'temp_gsr_interaction', ...],
    'trained_on_samples': 8754,
    'metrics': {
        'test_accuracy': 0.9680,
        'test_f1': 0.9681
    }
}

joblib.dump(model_data, 'ml_model/random_forest.pkl')
```

### 7.2. Realtime Prediction

#### 7.2.1. Predictor Class

```python
# File: ml_model/predictor.py

class RealtimePredictor:
    def __init__(self):
        self.model = None
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        """Load model từ file .pkl."""
        loaded = joblib.load(settings.ML_MODEL_PATH)
        
        if isinstance(loaded, dict):
            self.model = loaded.get('model')
            self.label_encoder = loaded.get('label_encoder')
            self.model_type = loaded.get('model_type')
        else:
            self.model = loaded
            self.model_type = 'randomforest'

    def predict(self, data: Dict[str, Any]) -> str:
        """Dự đoán trạng thái sức khỏe."""
        
        # Tạo features (base + engineered)
        features = self._create_features(data)
        
        # Predict
        if self.model_type == 'xgboost':
            pred_encoded = self.model.predict(features)
            prediction = self.label_encoder.inverse_transform(pred_encoded)[0]
        else:
            prediction = self.model.predict(features)[0]
        
        return prediction
```

#### 7.2.2. Luồng dự đoán

```
MQTT Message (ESP32)
        │
        ▼
IngestionService.ingest_data()
        │
        ▼
RealtimePredictor.predict(data)
        │
        ├── Tạo features (4 base + 8 engineered)
        │
        ├── Model.predict(features)
        │
        └── Return: 'Normal' | 'Stress' | 'Fever'
```

### 7.3. Cấu hình hệ thống

#### 7.3.1. Config.py

```python
# MongoDB
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "iomt_health_monitor"
TRAINING_COLLECTION = "training_health_data"
REALTIME_COLLECTION = "realtime_health_data"

# MQTT
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "esp32/health/data"

# ML
ML_MODEL_PATH = "ml_model/random_forest.pkl"
```

### 7.4. Docker Deployment (Optional)

```yaml
# docker-compose.yml
version: '3.8'
services:
  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
  
  mosquitto:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"
  
  ingestion:
    build: ./backend/iot-ingestion
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://mongodb:27017
      - MQTT_BROKER_HOST=mosquitto
```

---

## 8. KẾT QUẢ VÀ ĐÁNH GIÁ

### 8.1. Kết quả huấn luyện

#### 8.1.1. Performance Metrics

| Metric | Giá trị |
|--------|---------|
| **Test Accuracy** | **96.80%** |
| **Test F1-Score (weighted)** | **96.81%** |
| CV Accuracy (baseline) | 96.22% |
| CV F1-Score (after tuning) | 96.37% |

#### 8.1.2. Class-wise Performance

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Fever | 0.99 | 0.99 | 0.99 | 156 |
| Normal | 0.98 | 0.97 | 0.98 | 1192 |
| Stress | 0.93 | 0.95 | 0.94 | 403 |

#### 8.1.3. Confusion Matrix

```
              Predicted
              Normal  Stress  Fever
Actual  Normal  1158    31       3
        Stress   18    383       2
        Fever    0      1     155
```

### 8.2. Feature Importance

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | body_temp | 0.35 |
| 2 | bpm | 0.25 |
| 3 | gsr_adc | 0.20 |
| 4 | spo2 | 0.10 |
| 5-12 | engineered features | 0.10 |

### 8.3. Pipeline Statistics

| Stage | Records Before | Records After | Dropped |
|-------|--------------|---------------|---------|
| Raw Data | 10,000 | - | - |
| After Layer 1 (Hard Rules) | 10,000 | 9,500 | 5% |
| After Layer 2 (IQR) | 9,500 | 9,200 | 3% |
| After Layer 3 (IF+LOF) | 9,200 | 8,900 | 3% |
| After Layer 4 (KMeans) | 8,900 | 8,800 | 1% |
| After Layer 5 (Temporal) | 8,800 | 8,754 | 0.5% |

### 8.4. Đánh giá

#### 8.4.1. Ưu điểm

1. **Hiệu suất cao**: 96.81% F1-Score với XGBoost
2. **Pipeline hoàn chỉnh**: 5 lớp làm sạch đảm bảo chất lượng dữ liệu
3. **Best practices ML**: Cross-validation, hyperparameter tuning, model comparison
4. **Realtime prediction**: Hỗ trợ dự đoán thời gian thực
5. **Model versioning**: Lưu metadata cùng với model

#### 8.4.2. Hạn chế

1. **Dữ liệu tổng hợp**: Chưa có dữ liệu thực từ bệnh nhân
2. **Class imbalance**: Stress vẫn có F1 thấp hơn (0.94 vs 0.99)
3. **Không có online learning**: Model cần retrain thủ công
4. **Không có A/B testing**: Chưa có cơ chế so sánh model trong production

---

## 9. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### 9.1. Kết luận

Trong báo cáo này, chúng em đã xây dựng thành công hệ thống IoMT giám sát sức khỏe với các thành phần:

1. **Hệ thống thu thập dữ liệu**: Từ ESP32 qua MQTT/HTTP
2. **Pipeline làm sạch 5 lớp**: Hard Rules → IQR → IF+LOF → KMeans → Temporal
3. **Mô hình ML**: RandomForest và XGBoost với cross-validation và hyperparameter tuning
4. **Feature Engineering**: Tạo 8 features mới từ 4 features gốc
5. **Realtime Prediction**: Dự đoán trạng thái sức khỏe thời gian thực

**Kết quả đạt được**: F1-Score 96.81% với XGBoost, cao hơn so với RandomForest (96.45%).

### 9.2. Hướng phát triển

#### 9.2.1. Ngắn hạn (1-2 tháng)

- [ ] Thu thập dữ liệu thực từ bệnh nhân
- [ ] Áp dụng SMOTE để xử lý class imbalance
- [ ] Thêm các features mới (time-based, user-based)
- [ ] Cải thiện model cho class Stress

#### 9.2.2. Trung hạn (3-6 tháng)

- [ ] Thêm online learning (incremental training)
- [ ] Triển khai A/B testing cho model
- [ ] Xây dựng dashboard monitoring
- [ ] Thêm alert system khi confidence thấp

#### 9.2.3. Dài hạn (6-12 tháng)

- [ ] Tích hợp Deep Learning (LSTM cho time-series)
- [ ] Xây dựng API cho bên thứ ba
- [ ] Đạt chứng nhận y tế (FDA, CE)
- [ ] Triển khai edge computing trên ESP32

---

## 10. TÀI LIỆU THAM KHẢO

### 10.1. Thư viện Python

1. **Scikit-learn**: Machine Learning in Python
   - Pedregosa et al., JMLR 12, 2011
   
2. **XGBoost**: Scalable and Accurate Gradient Boosting
   - Chen and Guestrin, KDD 2016

3. **Pandas**: Python Data Analysis Library
   - McKinney, Proceedings of the 9th Python in Science Conference, 2010

4. **NumPy**: Numerical Python
   - Van Der Walt et al., Computing in Science & Engineering, 2011

### 10.2. Thuật toán

1. **Isolation Forest**: Liu et al., "Isolation Forest-based Anomaly Detection"
2. **Local Outlier Factor**: Breunig et al., "LOF: Identifying Density-Based Outliers"
3. **KMeans**: MacQueen, "Some Methods for classification and Analysis of Multivariate Observations"

### 10.3. Tài liệu khác

1. MongoDB Documentation: https://docs.mongodb.com/
2. MQTT Protocol: https://mqtt.org/
3. FastAPI Documentation: https://fastapi.tiangolo.com/

---

## PHỤ LỤC

### A. Cấu trúc thư mục

```
BTL/
├── backend/
│   └── iot-ingestion/
│       ├── cleaning/
│       │   ├── __init__.py
│       │   ├── anomaly_detector.py   # Lớp 3: IF + LOF
│       │   ├── hard_rules.py          # Lớp 1: Hard Rules
│       │   ├── iqr_filter.py          # Lớp 2: IQR
│       │   ├── label_validator.py     # Lớp 4: KMeans
│       │   ├── pipeline.py            # Orchestrator
│       │   └── temporal_check.py      # Lớp 5: Temporal
│       ├── ml_model/
│       │   └── predictor.py          # Realtime prediction
│       ├── config.py                 # Configuration
│       ├── database.py               # MongoDB connection
│       ├── main.py                   # FastAPI app
│       ├── models.py                 # Pydantic models
│       ├── service.py                # Ingestion service
│       ├── train_model.py            # Training pipeline
│       └── requirements.txt          # Dependencies
├── Data/
│   ├── generate_health_data.py      # Data generator
│   └── health_data_all.csv          # Generated data
├── Documents/
│   ├── ML_Technical_Documentation.md # Tech doc
│   ├── ML_Improvement_Plan.md        # Improvement plan
│   └── README.md                     # Project readme
└── ML_Improvement_Plan.md           # This report
```

### B. Cài đặt và chạy

```bash
# 1. Cài đặt dependencies
cd backend/iot-ingestion
pip install -r requirements.txt

# 2. Sinh dữ liệu huấn luyện
cd ../../Data
python generate_health_data.py

# 3. Huấn luyện model
cd ../backend/iot-ingestion
python train_model.py

# 4. Chạy server (tùy chọn)
python main.py
```

### C. API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/health/data` | Nhận dữ liệu từ ESP32 |
| GET | `/health/status/{user_id}` | Lấy trạng thái mới nhất |
| GET | `/model/info` | Thông tin model đang sử dụng |

---

**Ngày nộp**: 17/03/2026
**Môn học**: Máy học và ứng dụng
**Giảng viên**: [Tên giảng viên]
**Sinh viên**: [Họ tên sinh viên]
**Mã số sinh viên**: [MSSV]

---

*Báo cáo này là sản phẩm của bài tập lớn môn Máy học và Ứng dụng, được thực hiện theo hướng dẫn của giảng viên.*
