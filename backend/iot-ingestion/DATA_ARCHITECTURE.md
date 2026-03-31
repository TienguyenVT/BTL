# Tai Liệu Kiến Trúc Dữ Liệu — IoMT Health Monitor

## Mục Lục

- [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
- [Tầng 1 — MQTT (ESP32 → Node-RED)](#tầng-1--mqtt-esp32--node-red)
- [Tầng 2 — Data Lake (raw_sensor)](#tầng-2--data-lake-raw_sensor)
- [Tầng 3 — Data Warehouse (realtime_health_data)](#tầng-3--data-warehouse-realtime_health_data)
- [Tầng 4 — Training Data (training_health_data)](#tầng-4--training-data-training_health_data)
- [So Sánh 4 Tầng Dữ Liệu](#so-sánh-4-tầng-dữ-liệu)

---

## Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ESP32 (Embedded)                                   │
│  MAX30102 (BPM, SpO2) │ DS18B20 (Body Temp) │ GSR (Galvanic Skin Response) │
│  DHT11 (Room Temp/Humidity) ──► MQTT Broker (port 1883)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Node-RED (ETL Pipeline)                              │
│                                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────┐   ┌───────────────┐  │
│  │  MQTT    │──▶│  Cleansing   │──▶│    Feature     │──▶│   HTTP POST   │  │
│  │  Input   │   │  (Hard Rules │   │  Engineering   │   │  /predict    │  │
│  │          │   │   + IQR)     │   │  (12 features) │   │  FastAPI      │  │
│  └──────────┘   └──────────────┘   └────────────────┘   └───────┬───────┘  │
│                                                                 │           │
│                                         ┌───────────────────────┘           │
│                                         ▼                                   │
│                               ┌─────────────────┐                          │
│                               │  MongoDB Write  │                          │
│                               └────────┬────────┘                          │
└────────────────────────────────────────┼────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
           ┌──────────────┐     ┌──────────────────┐   ┌───────────────┐
           │  raw_sensor  │     │ realtime_health_ │   │ training_    │
           │  (Data Lake) │     │     data         │   │ health_data  │
           │  TTL 30 ngày │     │  (Data Warehouse)│   │  (Training)   │
           └──────────────┘     └──────────────────┘   └───────────────┘
```

---

## Tầng 1 — MQTT (ESP32 → Node-RED)

### Mô tả
Dữ liệu thô từ ESP32 được gửi qua giao thức **MQTT** lên broker (`mqtt://localhost:1883`), topic `esp32/health/data`. Đây là **điểm đầu vào** duy nhất của toàn hệ thống. Dữ liệu tại tầng này **chưa qua bất kỳ xử lý cleansing hay feature engineering** nào.

### Topic
```
esp32/health/data
```

### Payload ESP32 gửi lên (JSON)

```json
{
  "device_id": "ESP32_001",
  "mode": 1,
  "timestamp": 1711612800000,
  "bpm": 75.5,
  "spo2": 98.2,
  "body_temp": 36.7,
  "gsr_adc": 2250.0,
  "dht11_room_temp": 27.5,
  "dht11_humidity": 65.0,
  "confidence": 0.92,
  "dht11_bias": 0.2
}
```

### Mô tả các trường

| Trường | Kiểu | Nguồn | Mô tả | Phạm vi thường gặp |
|--------|------|-------|-------|---------------------|
| `device_id` | string | ESP32 | ID thiết bị ESP32 | `ESP32_001`, `ESP32_002`... |
| `mode` | int | ESP32 | Chế độ hoạt động | 0: nghỉ, 1: hoạt động, 2: calibration |
| `timestamp` | int64 | ESP32 | Unix timestamp milliseconds | - |
| `bpm` | float | MAX30102 | Nhịp tim từ PPG algorithm | 40–200 |
| `spo2` | float | MAX30102 | Độ bão hòa oxy trong máu | 50–100% |
| `body_temp` | float | DS18B20 | Nhiệt độ cơ thể (đã thermal compensation) | 35.0–39.5°C |
| `gsr_adc` | float | GSR Sensor | Điện trở da (ADC raw, đã calibration target 2200) | 500–5000 |
| `dht11_room_temp` | float | DHT11 | Nhiệt độ phòng (ambient) | 20–40°C |
| `dht11_humidity` | float | DHT11 | Độ ẩm không khí | 20–90% |
| `confidence` | float | MAX30102 | Độ tin cậy của PPG reading | 0.0–1.0 |
| `dht11_bias` | float | ESP32 | Hiệu chỉnh DHT11 so với DS18B20 | -5.0–5.0 |

### Trường KHÔNG gửi qua MQTT
- Các **engineered features** (8 features) — Node-RED tự tính
- **predicted_label** — FastAPI trả về sau khi predict

### Tầng này dùng để làm gì
- **Debug/lỗi**: Khi hệ thống báo lỗi, cần kiểm tra payload gốc từ ESP32
- **Phân tích chất lượng cảm biến**: Xem confidence, dht11_bias thay đổi theo thời gian
- **Tái hiện dữ liệu**: Nếu cleaning pipeline thay đổi, có thể chạy lại từ payload thô

---

## Tầng 2 — Data Lake (`raw_sensor`)

### Mô tả
Là tầng **lưu trữ thô** (raw data lake) — backup toàn bộ dữ liệu MQTT nhận được, **không qua bất kỳ xử lý cleansing nào**. Mục đích: **khôi phục dữ liệu** nếu cần chạy lại cleaning pipeline với logic mới, hoặc debug lỗi.

> **Đặc điểm quan trọng**: Dữ liệu tại đây **không có nhãn (label)**. Không dùng để training hay phân tích.

### TTL (Time-To-Live)
Tự động xóa sau **30 ngày** (2592000 giây) để tiết kiệm storage. Xóa dựa trên trường `ingested_at`.

### Collection
```
Database: iomt_health_monitor
Collection: raw_sensor
```

### Document Schema

```json
{
  "_id": ObjectId("..."),
  "device_id": "ESP32_001",
  "timestamp": 1711612800000,
  "bpm": 75.5,
  "spo2": 98.2,
  "body_temp": 36.7,
  "gsr_adc": 2250.0,
  "dht11_room_temp": 27.5,
  "dht11_humidity": 65.0,
  "confidence": 0.92,
  "dht11_bias": 0.2,
  "ingested_at": ISODate("2026-03-30T10:00:00.000Z")
}
```

### Mô tả các trường

| Trường | Kiểu | Mô tả | Ghi chú |
|--------|------|-------|---------|
| `_id` | ObjectId | ID tự động của MongoDB | Không dùng làm feature |
| `device_id` | string | ID thiết bị ESP32 | Metadata |
| `timestamp` | int64 | Unix ms từ ESP32 | Dùng để query theo thời gian |
| `bpm`, `spo2`, `body_temp`, `gsr_adc` | float | 4 sensor readings | Raw data — chưa clean |
| `dht11_room_temp`, `dht11_humidity` | float | DHT11 ambient data | Raw data |
| `confidence` | float | PPG confidence | Raw data |
| `dht11_bias` | float | Hiệu chỉnh DHT11 | Raw data |
| `ingested_at` | ISODate | Thời điểm ghi vào DB | **Dùng cho TTL index** |

### Trường bị loại bỏ ở các tầng phía dưới
- `mode` — chế độ ESP32, không phải chỉ số sinh lý
- `dht11_bias` — artifact hiệu chỉnh, không phải feature sinh lý

### Tầng này dùng để làm gì
- **Data recovery**: Chạy lại cleaning pipeline nếu logic thay đổi
- **Audit**: Kiểm tra dữ liệu gốc khi có dispute
- **Không dùng cho**: Training ML (vì không có nhãn, không clean)

### Indexes
```
1. TTL index: ingested_at (expireAfterSeconds=2592000 → 30 ngày)
2. Compound index: (device_id, ingested_at) — query nhanh theo thiết bị + thời gian
```

---

## Tầng 3 — Data Warehouse (`realtime_health_data`)

### Mô tả
Là tầng **dữ liệu đã xử lý đầy đủ** — sau khi MQTT payload qua Node-RED (cleansing + feature engineering), gọi `/predict` FastAPI để lấy nhãn, rồi ghi vào MongoDB. Đây là **tầng phân tích chính** cho dashboard, analytics, và alerting.

> **Đặc điểm quan trọng**: Tầng này chứa dữ liệu **thực tế** từ ESP32, **có nhãn dự đoán** (`predicted_label`), dùng cho dashboard hiển thị real-time.

### Collection
```
Database: iomt_health_monitor
Collection: realtime_health_data
```

### Document Schema

```json
{
  "_id": ObjectId("..."),
  "device_id": "ESP32_001",
  "timestamp": 1711612800000,
  "bpm": 75.5,
  "spo2": 98.2,
  "body_temp": 36.7,
  "gsr_adc": 2250.0,
  "bpm_spo2_ratio": 0.7703,
  "temp_gsr_interaction": 82.575,
  "bpm_temp_product": 2769.285,
  "spo2_gsr_ratio": 0.0436,
  "bpm_deviation": 0.5,
  "temp_deviation": 0.1,
  "gsr_deviation": 50.0,
  "physiological_stress_index": 0.0227,
  "predicted_label": "Normal",
  "confidence": 0.9234,
  "ingested_at": ISODate("2026-03-30T10:00:05.000Z")
}
```

### Mô tả các trường

| Trường | Kiểu | Mô tả | Ghi chú |
|--------|------|-------|---------|
| `_id` | ObjectId | ID tự động MongoDB | Không dùng làm feature |
| `device_id` | string | ID thiết bị ESP32 | Metadata — dùng filter dashboard |
| `timestamp` | int64 | Unix ms từ ESP32 | Dùng query theo thời gian |
| `bpm`, `spo2`, `body_temp`, `gsr_adc` | float | 4 sensor readings | **Đã cleanse** (loại outliers) |
| `bpm_spo2_ratio` | float | Engineered: `bpm / (spo2 + eps)` | Xem mục Feature Engineering |
| `temp_gsr_interaction` | float | Engineered: `body_temp * gsr_adc / 1000` | Xem mục Feature Engineering |
| `bpm_temp_product` | float | Engineered: `bpm * body_temp` | Xem mục Feature Engineering |
| `spo2_gsr_ratio` | float | Engineered: `spo2 / (gsr_adc + eps)` | Xem mục Feature Engineering |
| `bpm_deviation` | float | Engineered: `abs(bpm - 75)` | Xem mục Feature Engineering |
| `temp_deviation` | float | Engineered: `abs(body_temp - 36.8)` | Xem mục Feature Engineering |
| `gsr_deviation` | float | Engineered: `abs(gsr_adc - 2200)` | Xem mục Feature Engineering |
| `physiological_stress_index` | float | Engineered: `(bpm-75)/75 + (gsr-2200)/2200` | Xem mục Feature Engineering |
| `predicted_label` | string | Nhãn dự đoán từ ML model | `Normal`, `Stress`, `Fever` |
| `confidence` | float | Độ tin cậy của dự đoán (0.0–1.0) | Prob của class có xác suất cao nhất |
| `ingested_at` | ISODate | Thời điểm ghi vào DB | Dùng debug, không dùng feature |

### Trường bị loại bỏ
- `dht11_room_temp`, `dht11_humidity` — ambient data, không liên quan trực tiếp đến stress
- `dht11_bias`, `confidence` (ESP32), `mode` — artifact hoặc metadata không phải feature

### Các trường bị loại ở tầng Training (vì chỉ dùng 12 features)
- `predicted_label`, `confidence` — **tuyệt đối không đưa vào training features** (data leakage)

### Tầng này dùng để làm gì
- **Dashboard real-time**: Hiển thị dữ liệu ESP32 mới nhất
- **Alerting**: Cảnh báo khi `predicted_label` = `Fever` hoặc `confidence` thấp
- **Phân tích xu hướng**: Biểu đồ BPM/SpO2/Temp theo thời gian
- **Báo cáo**: Thống kê phân bố nhãn theo thiết bị/ngày

### Indexes
```
1. Compound index: (device_id, timestamp) — query nhanh theo thiết bị + thời gian
2. Single index: predicted_label — filter theo nhãn nhanh
```

---

## Tầng 4 — Training Data (`training_health_data`)

### Mô tả
Là tầng **dữ liệu huấn luyện** — dùng để train mô hình ML. Bao gồm **15,002 documents** được tạo từ `Data/health_data_all.csv` (9,914 mẫu gốc), sau khi gán nhãn bằng rule-based system và các script bổ sung.

> **Đặc điểm quan trọng**: Đây là dữ liệu **tổng hợp (synthetic + semi-synthetic)** — không phải 100% từ ESP32 thực. Cần thu thập thêm dữ liệu thực từ `realtime_health_data` để cải thiện model.

### Collection
```
Database: iomt_health_monitor
Collection: training_health_data
```

### Document Schema (sau khi cleanup)

```json
{
  "_id": ObjectId("..."),
  "device_id": "ESP32_SYNTHETIC",
  "timestamp": 1768096440000,
  "bpm": 78.0,
  "spo2": 98.4,
  "body_temp": 36.6,
  "gsr_adc": 2697.9,
  "bpm_spo2_ratio": 0.7924,
  "temp_gsr_interaction": 98.7354,
  "bpm_temp_product": 2854.6975,
  "spo2_gsr_ratio": 0.0365,
  "bpm_deviation": 3.004,
  "temp_deviation": 0.2032,
  "gsr_deviation": 497.9209,
  "physiological_stress_index": 0.26638,
  "ingested_at": ISODate("2026-01-11T01:54:00.000Z"),
  "label": "Normal"
}
```

### Mô tả các trường

| Trường | Kiểu | Vai trò | Ghi chú |
|--------|------|---------|---------|
| `_id` | ObjectId | Metadata | Bỏ khi train (`{'_id': 0}`) |
| `device_id` | string | Metadata | Chủ yếu `ESP32_SYNTHETIC` |
| `timestamp` | int64 | Metadata | Không dùng train |
| `bpm`, `spo2`, `body_temp`, `gsr_adc` | float | **Feature (raw)** | 4 features gốc |
| `bpm_spo2_ratio` | float | **Feature (engineered)** | 8 features tương tác |
| `temp_gsr_interaction` | float | **Feature (engineered)** | |
| `bpm_temp_product` | float | **Feature (engineered)** | |
| `spo2_gsr_ratio` | float | **Feature (engineered)** | |
| `bpm_deviation` | float | **Feature (engineered)** | |
| `temp_deviation` | float | **Feature (engineered)** | |
| `gsr_deviation` | float | **Feature (engineered)** | |
| `physiological_stress_index` | float | **Feature (engineered)** | |
| `ingested_at` | ISODate | Metadata | Không dùng train |
| `label` | string | **TARGET** | `Normal`, `Stress`, `Fever` |

### 12 Features dùng để train (đúng)

```
Raw (4):
  1. bpm
  2. spo2
  3. body_temp
  4. gsr_adc

Engineered (8):
  5.  bpm_spo2_ratio           = bpm / (spo2 + eps)
  6.  temp_gsr_interaction     = body_temp * gsr_adc / 1000
  7.  bpm_temp_product         = bpm * body_temp
  8.  spo2_gsr_ratio           = spo2 / (gsr_adc + eps)
  9.  bpm_deviation            = abs(bpm - 75)
  10. temp_deviation           = abs(body_temp - 36.8)
  11. gsr_deviation            = abs(gsr_adc - 2200)
  12. physiological_stress_index = (bpm-75)/75 + (gsr_adc-2200)/2200
```

### Các trường đã bị LOẠI BỎ (cleanup)

| Trường | Lý do loại |
|--------|-----------|
| `predicted_label` | **Data leakage** — là output của model, tuyệt đối không đưa vào features |
| `confidence` | Confidence của prediction, không phải feature sinh lý |
| `label_source` | Metadata quá trình gán nhãn |
| `invalid_reading` | Metadata chất lượng dữ liệu |
| `gsr_threshold_used` | Metadata threshold GSR |
| `unstable_window` | Metadata cảnh báo |

### Nhãn (Target Labels)

| Nhãn | Số lượng | Đặc điểm sinh lý |
|------|----------|-------------------|
| `Normal` | ~11,000 | BPM 60–90, SpO2 95–100%, Temp 36.0–37.0, GSR 1500–2800 |
| `Stress` | ~2,400 | BPM >90, GSR >3000, Temp ổn định |
| `Fever` | ~1,000 | Temp >37.5, BPM tăng nhẹ, GSR thay đổi |

### Tầng này dùng để làm gì
- **Train ML model**: Input cho `train_enhanced.py`
- **Validate model**: Cross-validation, confusion matrix, feature importance
- **Đánh giá chất lượng dữ liệu**: Phân tích phân bố, correlation matrix

### Pipeline huấn luyện

```
training_health_data (MongoDB)
         │
         ▼
  Read: { _id: 0, <12 features>, label }
         │
         ▼
  Feature Engineering (8 engineered features)
         │
         ▼
  Train/Test Split (80/20, stratified)
         │
         ├─── Baseline: GridSearchCV (RF + XGBoost)
         ├─── Optuna: Bayesian Optimization (RF + XGBoost)
         └─── Evaluate + Save model
                   │
                   ▼
         ml_model/random_forest.pkl
```

---

## So Sánh 4 Tầng Dữ Liệu

| Tiêu chí | MQTT (ESP32) | Data Lake (raw_sensor) | Data Warehouse (realtime) | Training Data |
|----------|-------------|------------------------|---------------------------|----------------|
| **Trạng thái** | Thô | Thô | Đã clean + engineered | Đã clean + engineered |
| **Nhãn (label)** | Không | Không | Có (ML predict) | Có (rule-based) |
| **Features** | 0 (raw thô) | 0 (raw thô) | 12 (clean) | 12 (clean) |
| **Nguồn** | ESP32 thực | ESP32 thực | ESP32 thực (clean) | Synthetic + CSV |
| **Thời gian lưu** | Tức thời | 30 ngày (TTL) | Vĩnh viễn | Vĩnh viễn |
| **Dùng cho ML train** | Không | Không | **Có thể** (cần gán nhãn thủ công) | **Có** (chính) |
| **Dùng cho dashboard** | Không | Không | **Có** | Không |
| **Dùng cho debug** | Không | **Có** | **Có** | Không |
| **Feature engineering** | Không | Không | Node-RED | Python script |
| **Có predicted_label?** | Không | Không | **Có** | **Có** (cần loại bỏ khi train) |

### Luồng dữ liệu giữa các tầng

```
1. ESP32 ──MQTT──► raw_sensor (backup thô, TTL 30 ngày)

2. ESP32 ──MQTT──► Node-RED ──clean+engineer──► FastAPI /predict
                                                                   │
3. ESP32 ──MQTT──► Node-RED ──clean+engineer──► realtime_health_data
                                                                   │
4. CSV ──import──► training_health_data ──train──► ml_model.pkl ◄──┘
                                                           │
                                                           ▼
                                              FastAPI /predict ◄──┘
```

### Lưu ý quan trọng khi sử dụng

1. **Tầng Training không nên mix dữ liệu realtime chưa gán nhãn** — nếu muốn bổ sung dữ liệu từ `realtime_health_data`, cần:
   - Chạy rule-based labeling trước
   - Hoặc gán nhãn thủ công (human annotation)
   - Tuyệt đối không dùng `predicted_label` từ model hiện tại để train lại (data leakage)

2. **Data Lake là tầng an toàn** — khi thay đổi cleaning pipeline, luôn có thể replay từ `raw_sensor`

3. **12 features nhất quán** — cả 3 tầng (realtime, training, inference) đều dùng cùng 12 features để đảm bảo model không bị train trên features khác với inference
