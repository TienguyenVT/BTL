# Kế hoạch cải thiện Machine Learning cho hệ thống IoMT

## 1. Đánh giá hiện trạng ML

### Điểm mạnh
- Sử dụng RandomForest Classifier - thuật toán phù hợp cho bài toán phân loại đa lớp
- Pipeline làm sạch 5 lớp khá hoàn chỉnh (Hard Rules → IQR → IF+LOF → KMeans → Temporal)
- Có visualization: confusion matrix, feature importance, phân bố sinh lý, ma trận tương quan
- Tách biệt rõ ràng: training pipeline vs realtime prediction

### Điểm cần cải thiện
| Vấn đề | Mức độ ưu tiên |
|--------|----------------|
| Thiếu cross-validation khi huấn luyện | Cao |
| Không có hyperparameter tuning | Cao |
| Dữ liệu huấn luyện được sinh ra có vấn đề (noise + label mismatch) | Cao |
| Thiếu model versioning | Trung bình |
| Không có A/B testing hoặc model rollback | Trung bình |
| Thiếu monitoring real-time accuracy | Thấp |

---

## 2. Kế hoạch chi tiết

### Giai đoạn 1: Cải thiện Training Pipeline (train_model.py)

#### 1.1 Thêm Cross-Validation
```python
# Thêm vào train_model.py
from sklearn.model_selection import cross_val_score, StratifiedKFold

# 5-fold stratified cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(rf_model, X, y, cv=cv, scoring='accuracy')
print(f"Cross-validation Accuracy: {cv_scores.mean():.2f}% (+/- {cv_scores.std()*2:.2f}%)")
```

#### 1.2 Hyperparameter Tuning với GridSearchCV
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

grid_search = GridSearchCV(RandomForestClassifier(random_state=42), 
                           param_grid, cv=3, scoring='f1_weighted', n_jobs=-1)
grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_
```

#### 1.3 Thêm Model Versioning
```python
import mlflow

# Track experiments với MLflow
mlflow.set_experiment("IoMT_Health_Classification")
with mlflow.start_run():
    mlflow.log_param("n_estimators", 200)
    mlflow.log_metric("accuracy", accuracy)
    mlflow.sklearn.log_model(rf_model, "model")
```

---

### Giai đoạn 2: Cải thiện Data Generator (generate_health_data.py)

#### 2.1 Sửa lỗi Logic Noise Injection
**Vấn đề hiện tại**: Khi inject noise, có 50% label vẫn giữ nguyên → gây mismatch giữa features và label

**Giải pháp**:
- Khi inject noise → label luôn là 'Error' (hoặc bỏ hẳn bản ghi đó)
- Hoặc tạo 2 dataset riêng: clean data cho training, noisy data cho cleaning pipeline test

#### 2.2 Cân bằng lớp (Class Balancing)
**Vấn đề**: SCENARIO_WEIGHTS = [0.7, 0.2, 0.1] → class imbalance

**Giải pháp**: Thêm SMOTE hoặc oversampling:
```python
from imblearn.over_sampling import SMOTE
smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X, y)
```

---

### Giai đoạn 3: Nâng cao Model Performance

#### 3.1 Thử nghiệm nhiều thuật toán
- XGBoost / LightGBM (thường tốt hơn RandomForest)
- Neural Network (MLPClassifier) cho comparison
- Ensemble voting classifier

#### 3.2 Thêm Feature Engineering
```python
# Tạo thêm features
df['bpm_spo2_ratio'] = df['bpm'] / df['spo2']
df['temp_gsr_interaction'] = df['body_temp'] * df['gsr_adc']
df['hrv_estimate'] = 1 / (df['bpm'] / 60)  # Giả định
```

#### 3.3 Calibration
```python
from sklearn.calibration import CalibratedClassifierCV
calibrated_model = CalibratedClassifierCV(rf_model, cv=3)
calibrated_model.fit(X_train, y_train)
```

---

### Giai đoạn 4: Monitoring & Production-Ready

#### 4.1 Model Registry
```python
# Lưu model với version
import shutil
version = datetime.now().strftime("%Y%m%d_%H%M%S")
model_path = f"ml_model/versions/rf_{version}.pkl"
joblib.dump(best_model, model_path)
```

#### 4.2 Re-training Scheduler
- Tự động retrain mỗi tuần/tháng
- So sánh model mới vs cũ trước khi deploy

#### 4.3 Real-time Monitoring
- Log prediction confidence (predict_proba)
- Alert khi confidence thấp
- Track accuracy qua feedback loop

---

## 3. Timeline đề xuất

| Giai đoạn | Nội dung | Thời gian |
|-----------|----------|-----------|
| 1 | Cross-validation + Hyperparameter tuning | 1 tuần |
| 2 | Sửa data generator + Class balancing | 1 tuần |
| 3 | Feature engineering + Algorithm comparison | 2 tuần |
| 4 | Model versioning + Monitoring | 1 tuần |

---

## 4. Điểm cần trao đổi thêm với giảng viên

1. **Mục tiêu chính của môn học**: Học sinh cần demonstrate kiến thức ML hay là build production system?
2. **Giới hạn thời gian**: Có đủ thời gian để implement hết các improvements không?
3. **Đánh giá**: Tiêu chí chấm điểm có weights cho từng phần (data prep, model, deployment) không?

---

## 5. Đề xuất điểm chấm (Grading)

Nếu đánh giá trên phương diện Machine Learning thuần túy:

| Thành phần | Điểm hiện tại (ước tính) | Điểm tối đa |
|------------|--------------------------|-------------|
| Data preprocessing pipeline | 7/10 | 10 |
| Model selection | 6/10 | 10 |
| Model training & evaluation | 6/10 | 10 |
| Cross-validation | 0/10 | 10 |
| Hyperparameter tuning | 0/10 | 10 |
| Model versioning | 0/10 | 10 |
| Feature engineering | 3/10 | 10 |
| Visualization & reporting | 8/10 | 10 |

**Tổng điểm ước tính: ~4.5/7 (64/100)**

**Đề xuất điểm: 7-7.5/10** (nếu implement được Phase 1 + 2)
