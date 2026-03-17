# Tài liệu Kỹ thuật - Machine Learning trong Hệ thống IoMT Health Monitor

## Mục lục
1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Thư viện sử dụng và vai trò](#2-thư-viện-sử-dụng-và-vai-trò)
3. [Cấu hình hệ thống](#3-cấu-hình-hệ-thống)
4. [Mô hình Machine Learning](#4-mô-hình-machine-learning)
5. [Pipeline làm sạch dữ liệu (5 lớp)](#5-pipeline-làm-sạch-dữ-liệu-5-lớp)
6. [Huấn luyện mô hình](#6-huấn-luyện-mô-hình)
7. [Dự đoán thời gian thực](#7-dự-đoán-thời-gian-thực)

---

## 1. Tổng quan hệ thống

Hệ thống **IoMT Health Monitor** sử dụng Machine Learning để:
- **Phân loại trạng thái sức khỏe** từ dữ liệu cảm biến ESP32
- **3 nhãn phân loại**: `Normal`, `Stress`, `Fever`
- **4 features đầu vào**: `bpm`, `spo2`, `body_temp`, `gsr_adc`

### Kiến trúc ML
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data Generator │────▶│ Cleaning Pipeline │────▶│  Model Training │
│  (CSV/Database) │     │   (5 Layers)      │     │ (RF/XGBoost)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   ESP32 Sensor  │────▶│ Realtime Predictor│◀────│    ML Model     │
│   (MQTT/HTTP)   │     │  (predictor.py)  │     │    (.pkl)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 2. Thư viện sử dụng và vai trò

### 2.1 Core Dependencies

| Thư viện | Phiên bản | Vai trò |
|----------|-----------|---------|
| **pandas** | 2.2.1 | Xử lý và phân tích dữ liệu dạng bảng |
| **numpy** | 1.26.4 | Tính toán số học, xử lý mảng đa chiều |
| **scikit-learn** | >=1.4.1 | ML algorithms, cross-validation, preprocessing |
| **scipy** | 1.12.0 | Tính toán thống kê (IQR, distribution) |

### 2.2 Model Training & Evaluation

| Thư viện | Phiên bản | Vai trò |
|----------|-----------|---------|
| **xgboost** | >=2.0.0 | Gradient Boosting Classifier (so sánh với RF) |
| **joblib** | 1.3.2 | Lưu/trload model (.pkl) |
| **imbalanced-learn** | >=0.12.0 | SMOTE cho xử lý class imbalance |

### 2.3 Data Visualization

| Thư viện | Phiên bản | Vai trò |
|----------|-----------|---------|
| **matplotlib** | >=3.8.3 | Vẽ đồ thị, visualization |
| **seaborn** | >=0.13.2 | Statistical graphics (heatmap, boxplot) |

### 2.4 Infrastructure

| Thư viện | Phiên bản | Vai trò |
|----------|-----------|---------|
| **pymongo** | 4.7.1 | MongoDB driver cho data storage |
| **python-dotenv** | >=1.0.1 | Load biến môi trường từ .env |

---

## 3. Cấu hình hệ thống

File cấu hình: `config.py`

### 3.1 MongoDB Configuration

```python
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "iomt_health_monitor")

# Collections
TRAINING_COLLECTION: str = "training_health_data"      # Dữ liệu huấn luyện
REALTIME_COLLECTION: str = "realtime_health_data"      # Dữ liệu thời gian thực
```

### 3.2 MQTT Configuration

```python
MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "esp32/health/data")
MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "iomt-ingestion-service")
```

### 3.3 ML Configuration

```python
ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "ml_model/random_forest.pkl")
CSV_DATA_PATH: str = os.getenv("CSV_DATA_PATH", "../../Data/health_data_all.csv")
```

---

## 4. Mô hình Machine Learning

### 4.1 Mô hình chính: RandomForest Classifier

**RandomForest** là mô hình ensemble learning, kết hợp nhiều decision trees.

#### Hyperparameters (sau GridSearchCV)

| Parameter | Giá trị tối ưu | Ý nghĩa |
|-----------|----------------|----------|
| `n_estimators` | 100 | Số lượng cây quyết định |
| `max_depth` | None (unlimited) | Độ sâu tối đa của cây |
| `min_samples_split` | 2 | Số mẫu tối thiểu để chia node |
| `min_samples_leaf` | 1 | Số mẫu tối thiểu ở node lá |
| `class_weight` | None | Trọng số cho các lớp |

### 4.2 Mô hình so sánh: XGBoost

**XGBoost** (eXtreme Gradient Boosting) được sử dụng để so sánh và chọn mô hình tốt hơn.

| Parameter | Giá trị mặc định | Ý nghĩa |
|-----------|------------------|----------|
| `n_estimators` | 200 | Số vòng boosting |
| `max_depth` | 10 | Độ sâu tối đa |
| `learning_rate` | 0.1 | Tốc độ học (eta) |
| `eval_metric` | mlogloss | Hàm mất mát multi-class |

### 4.3 Các thuật toán phát hiện bất thường

#### Isolation Forest (`anomaly_detector.py`)
- **Mục đích**: Phát hiện anomaly đa biến
- **Tham số**:
  - `contamination`: 0.05 (5% dữ liệu là anomaly)
  - `random_state`: 42
  - `n_jobs`: -1 (parallel)

#### Local Outlier Factor (`anomaly_detector.py`)
- **Mục đích**: Phát hiện outlier dựa trên local density
- **Tham số**:
  - `n_neighbors`: 20
  - `contamination`: 0.05

### 4.4 Thuật toán validation: KMeans

| Parameter | Giá trị | Ý nghĩa |
|-----------|---------|----------|
| `n_clusters` | 3 | Số cụm = số nhãn |
| `random_state` | 42 | Reproducibility |
| `n_init` | 10 | Số lần chạy với init khác nhau |

---

## 5. Pipeline làm sạch dữ liệu (5 lớp)

Pipeline làm sạch 5 lớp được thiết kế để đảm bảo chất lượng dữ liệu huấn luyện.

```
Raw Data → Lớp 1 (Hard Rules) → Lớp 2 (IQR) → Lớp 3 (IF+LOF) 
        → Lớp 4 (KMeans) → Lớp 5 (Temporal) → Clean Data
```

### 5.1 Lớp 1: Hard Rules Filtering (`hard_rules.py`)

**Mục đích**: Loại bỏ giá trị vật lý/sinh lý không hợp lệ

**Ngưỡng sinh lý**:

| Chỉ số | Giới hạn dưới | Giới hạn trên | Ý nghĩa |
|--------|---------------|---------------|---------|
| `bpm` | 40 | 200 | Nhịp tim nhân tạo |
| `spo2` | 80 | 100 | SpO2 % |
| `body_temp` | 34 | 42 | Nhiệt độ °C |
| `gsr_adc` | 0.01 | ∞ | Điện trở da |
| `ext_temp_c` | -10 | 50 | Nhiệt độ ngoài trời |
| `ext_humidity_pct` | 0 | 100 | Độ ẩm % |

**Xử lý**:
1. Loại bỏ bản ghi có nhãn `Error`
2. Giá trị ngoài ngưỡng → NaN

### 5.2 Lớp 2: IQR Filter (`iqr_filter.py`)

**Mục đích**: Phát hiện và xử lý outlier bằng IQR (Interquartile Range)

**Phương pháp**:
- Tính IQR cho từng nhãn riêng biệt
- Ngưỡng: `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`
- Giá trị ngoài ngưỡng → NaN
- Áp dụng **Linear Interpolation** để lấp đầy NaN

**Features áp dụng**: `bpm`, `spo2`, `body_temp`, `gsr_adc`

### 5.3 Lớp 3: Anomaly Detection (`anomaly_detector.py`)

**Mục đích**: Phát hiện anomaly đa biến bằng ensemble methods

**Phương pháp**:
1. **Isolation Forest**: Cô lập anomaly bằng random partitioning
2. **Local Outlier Factor**: So sánh local density với neighbors
3. **Consensus**: Chỉ loại bỏ khi CẢ HAI đánh dấu là anomaly

**Tham số**:
- `contamination`: 0.05 (5%)
- `n_neighbors` (LOF): 20
- Minimum samples per label: 30

### 5.4 Lớp 4: Label Validation (`label_validator.py`)

**Mục đích**: Xác thực nhãn bằng clustering

**Phương pháp**:
1. KMeans clustering (k=3)
2. Ánh xạ cluster → nhãn phổ biến nhất trong cluster
3. Loại bỏ bản ghi có nhãn gốc ≠ nhãn cluster

**Kết quả**: Tỷ lệ đồng thuận nhãn được in ra

### 5.5 Lớp 5: Temporal Check (`temporal_check.py`)

**Mục đích**: Đảm bảo tính nhất quán thời gian

**Xử lý**:
1. **Label Smoothing**: Sửa nhãn đột biến theo nhãn đa số trong cửa sổ
   - Window size: 5
   - Dominance threshold: 75%
2. **Signal Smoothing**: Moving Average cho `bpm` và `gsr_adc`
   - Smoothing window: 5

---

## 6. Huấn luyện mô hình

File: `train_model.py`

### 6.1 Quy trình huấn luyện

```
┌─────────────────────┐
│  1. Load Data       │
│  (MongoDB)         │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  2. Feature         │
│  Engineering        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  3. Baseline CV    │
│  (5-fold)          │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  4. GridSearchCV   │
│  (Hyperparameter)   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  5. XGBoost        │
│  Comparison        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  6. Select Best    │
│  Model             │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  7. Retrain Full   │
│  + Save .pkl       │
└─────────────────────┘
```

### 6.2 Feature Engineering

**8 engineered features** được tạo thêm:

| Feature | Công thức | Ý nghĩa |
|---------|-----------|---------|
| `bpm_spo2_ratio` | bpm / spo2 | Tỷ lệ nhịp tim/spo2 |
| `temp_gsr_interaction` | body_temp * gsr_adc / 1000 | Tương tác nhiệt-GSR |
| `bpm_temp_product` | bpm * body_temp | Tích nhịp-nhiệt |
| `spo2_gsr_ratio` | spo2 / gsr_adc | Tỷ lệ spo2/gsr |
| `bpm_deviation` | \|bpm - 75\| | Độ lệch BPM |
| `temp_deviation` | \|body_temp - 36.8\| | Độ lệch nhiệt độ |
| `gsr_deviation` | \|gsr_adc - 2200\| | Độ lệch GSR |
| `physiological_stress_index` | (bpm-75)/75 + (gsr-2200)/2200 | Chỉ số stress tổng hợp |

### 6.3 Cross-Validation

**5-Fold Stratified Cross-Validation**:
- Đảm bảo tỷ lệ class được giữ nguyên trong mỗi fold
- Metrics: Accuracy, F1-Score (weighted & macro), Precision, Recall
- Confidence Interval 95%

### 6.4 Hyperparameter Tuning

**GridSearchCV** với:
- `n_estimators`: [100, 200, 300]
- `max_depth`: [10, 20, None]
- `min_samples_split`: [2, 5, 10]
- `min_samples_leaf`: [1, 2, 4]
- `class_weight`: [None, 'balanced']

**Scoring**: F1-weighted (phù hợp với imbalanced data)

### 6.5 Model Comparison

So sánh RandomForest (best params) vs XGBoost:
- Chọn model có F1-score cao hơn
- Lưu model kèm metadata (version, features, metrics)

---

## 7. Dự đoán thời gian thực

File: `ml_model/predictor.py`

### 7.1 RealtimePredictor Class

```python
class RealtimePredictor:
    def __init__(self):
        self.model = None
        self.is_loaded = False
        self._load_model()

    def predict(self, data: Dict[str, Any]) -> str:
        # Trả về: 'Normal', 'Stress', 'Fever'
```

### 7.2 Luồng dự đoán

1. **Load model** từ `.pkl` (khởi động 1 lần)
2. **Tiếp nhận data** từ MQTT/HTTP
3. **Tạo features** (base + engineered)
4. **Predict** với model đã train
5. **Trả về nhãn**: Normal/Stress/Fever

### 7.3 Model Metadata (Versioning)

```python
{
    'model': <trained_model>,
    'model_type': 'xgboost' | 'randomforest',
    'version': '20260317_103045',  # timestamp
    'features': ['bpm', 'spo2', 'body_temp', 'gsr_adc', ...],
    'trained_on_samples': 8754,
    'best_params': {...},
    'metrics': {'test_accuracy': 0.968, 'test_f1': 0.9681}
}
```

---

## 8. Kết quả hiện tại

| Metric | Giá trị |
|--------|---------|
| CV Accuracy | 96.22% |
| CV F1-Score (after tuning) | 96.37% |
| XGBoost Test Accuracy | 96.80% |
| XGBoost Test F1-Score | 96.81% |
| **Model được chọn** | **XGBoost** |

### Class-wise Performance

| Class | Precision | Recall | F1-Score |
|-------|-----------|--------|----------|
| Fever | 0.99 | 0.99 | 0.99 |
| Normal | 0.98 | 0.97 | 0.98 |
| Stress | 0.93 | 0.95 | 0.94 |

---

## 9. Các file chính

| File | Mô tả |
|------|-------|
| `train_model.py` | Pipeline huấn luyện đầy đủ |
| `ml_model/predictor.py` | Dự đoán thời gian thực |
| `cleaning/pipeline.py` | Orchestrator cho 5 lớp cleaning |
| `cleaning/hard_rules.py` | Lớp 1: Hard rule filtering |
| `cleaning/iqr_filter.py` | Lớp 2: IQR outlier detection |
| `cleaning/anomaly_detector.py` | Lớp 3: IF + LOF anomaly detection |
| `cleaning/label_validator.py` | Lớp 4: KMeans label validation |
| `cleaning/temporal_check.py` | Lớp 5: Temporal consistency |
| `Data/generate_health_data.py` | Sinh dữ liệu huấn luyện |
| `config.py` | Cấu hình hệ thống |

---

## 10. Cải thiện đã thực hiện

### Phase 1: Cơ bản
- ✅ Cross-validation (5-fold Stratified)
- ✅ Hyperparameter Tuning (GridSearchCV)
- ✅ Visualization (confusion matrix, feature importance)

### Phase 2: Nâng cao  
- ✅ Sửa lỗi data generator (label mismatch)
- ✅ Cân bằng class distribution [0.5, 0.3, 0.2]
- ✅ Feature Engineering (8 new features)
- ✅ XGBoost comparison
- ✅ Model Versioning

---

*Document created: 2026-03-17*
*Last updated: 2026-03-17*
