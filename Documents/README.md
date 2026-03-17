# 🏥 Hệ thống IoMT Giám sát Sức khỏe (Health Monitoring System)

Dự án Hệ thống Internet of Medical Things (IoMT) giám sát sức khỏe thời gian thực. Hệ thống sử dụng kiến trúc **Modular Monolith** kết hợp **Hybrid Backend**, nhận dữ liệu từ cảm biến qua ESP32, làm sạch dữ liệu qua pipeline 5 lớp bằng Machine Learning, và hiển thị trên Dashboard giao diện web.

## 📐 Kiến trúc Hệ thống

Hệ thống được chia thành 3 phần chính giao tiếp theo mô hình Shared Database:

1. **IoT Ingestion Module (Python)**: Chuyên nhận dữ liệu thô từ ESP32 qua giao thức MQTT hoặc HTTP POST. Dữ liệu này sau đó đi qua một Pipeline làm sạch 5 lớp (dựa trên thuật toán AI/ML) để loại bỏ nhiễu và lưu vào cơ sở dữ liệu MongoDB.
2. **Web Dashboard Module (Java Spring Boot)**: Cung cấp RESTful API cho Frontend. Module này được thiết kế thuần tủy cấu hình **Trực đọc (Read-only)** từ MongoDB nhằm truy xuất dữ liệu sức khỏe đã được làm sạch, đảm bảo an toàn dữ liệu và tối ưu hiệu suất truy vấn.
3. **Frontend Dashboard (React + TypeScript + Tailwind CSS)**: Giao diện trực quan cho người dùng, hiển thị các chỉ số sinh lý (Nhịp tim, SpO2, Huyết áp, Điện trở da) và biểu đồ lịch sử theo thời gian thực. Được thiết kế tối ưu trên cả nền tảng Mobile và Desktop.

### 🔄 Luồng dữ liệu (Data Flow)

```text
[ESP32 / Sensors] 
       │ (MQTT / HTTP JSON)
       ▼
[Python Ingestion] ──(Lưu rác)──▶ (Collection: raw_health_data)
       │
      (Pipeline 5 Lớp Làm Sạch)
       │
       ▼
 [Shared MongoDB] ◀──(Lưu sạch)── (Collection: clean_health_data)
       │
      (Đọc dữ liệu)
       ▼
[Java Spring Boot] ──(REST API)──▶ [React Frontend Dashboard]
```

---

## 📂 Cấu trúc Thư mục

```text
C:\Documents\BTL\
├── backend/
│   ├── iot-ingestion/       # Module 1: Xử lý dữ liệu IoT (Python / FastAPI / MQTT)
│   │   ├── cleaning/        # Logic làm sạch 5 lớp
│   │   ├── main.py          # Entry point
│   │   └── requirements.txt
│   │
│   └── web-dashboard/       # Module 2: REST API (Java / Spring Boot 3)
│       ├── pom.xml          # Maven config
│       └── src/main/java/   # Mã nguồn Java (Service, Controller, Repository)
│
└── frontend/                # Module 3: Giao diện người dùng (React / Vite)
    ├── package.json
    ├── tailwind.config.js   # Cấu hình UI framework
    └── src/                 # Component, Pages, API services
```

---

## 🛠 Yêu cầu Hệ thống (Prerequisites)

Để chạy dự án này trên máy local, bạn cần cài đặt:
- **MongoDB** (chạy tại `mongodb://localhost:27017`)
- **MQTT Broker** (ví dụ: Mosquitto chạy tại `localhost:1883`)
- **Python 3.9+** (cho Ingestion Module)
- **Java 17 & Maven** (cho Web Dashboard Module)
- **Node.js 18+** (cho Frontend)

---

## 🚀 Hướng dẫn Cài đặt & Chạy

Bạn cần mở 3 Terminal riêng biệt để chạy 3 thành phần của hệ thống.

### 1. Khởi chạy IoT Ingestion (Python)

Mở Terminal 1:
```bash
cd backend/iot-ingestion
pip install -r requirements.txt
# Copy file cấu hình môi trường
cp .env.example .env 
# (Tùy chọn) Chỉnh sửa cấu hình trong file .env nếu cần
python main.py
```
*Dịch vụ sẽ chạy ở cổng `8000`. Hỗ trợ nhận MQTT và HTTP.*

### 2. Khởi chạy Web Dashboard API (Java)

Mở Terminal 2:
```bash
cd backend/web-dashboard
mvn spring-boot:run
```
*API Backend sẽ chạy ở cổng `8080`. Bạn có thể xem tài liệu API Swagger tại: `http://localhost:8080/swagger-ui.html`*

### 3. Khởi chạy Frontend (React)

Mở Terminal 3:
```bash
cd frontend
npm install
npm run dev
```
*Giao diện Web sẽ chạy ở cổng `5173`. Truy cập `http://localhost:5173` trên trình duyệt.*

---

## 📡 Chi tiết REST API (Backend - Cổng 8080)

Các API được cung cấp bởi module Spring Boot để phục vụ dữ liệu cho Frontend.

| Endpoint | Method | Params | Chức năng |
|----------|--------|--------|-----------|
| `/api/health/latest` | `GET` | `userId=xyz` | Lấy 1 bản ghi gần nhất của user để hiển thị trên thẻ Dashboard |
| `/api/health/history`| `GET` | `userId=xyz`, `hours=24` | Lấy danh sách dữ liệu trong 24h qua cho Biểu đồ đường (Line Chart) |
| `/api/health/recent` | `GET` | `userId=xyz`, `limit=20` | Lấy N bản ghi gần nhất dưới dạng danh sách rút gọn |

---

## 🧠 Chi tiết Pipeline Làm sạch Dữ liệu (Python Ingestion)

Mọi dữ liệu đẩy lên từ thiết bị ESP32 đều phải trải qua 5 bước kiểm duyệt trước khi Frontend có thể nhìn thấy:

1. **Lớp 1 (Hard Rules)**: Lọc các giá trị ngoài giới hạn sinh lý thực tế (VD: Nhịp tim > 200 BPM, SpO2 < 80% được coi là lỗi cảm biến và loại bỏ).
2. **Lớp 2 (IQR Filter)**: Thuật toán thống kê IQR loại bỏ các giá trị ngoại lai (Anomalies) trong từng đặc trưng dữ liệu.
3. **Lớp 3 (Anomaly Detector)**: Cảnh báo bất thường qua đánh giá đa biến đồng thuận (Consensus) bằng 2 model: *Isolation Forest* và *Local Outlier Factor (LOF)*.
4. **Lớp 4 (Label Validator)**: Dùng thuật toán *KMeans Clustering (k=3)* gom cụm dữ liệu để kiểm chứng nhãn sức khỏe (Normal/Stress/Fever). Lọc bỏ các trạng thái không trùng khớp.
5. **Lớp 5 (Temporal Check)**: Kiểm tra thông qua cửa sổ trượt (Sliding Window), đảm bảo tính nhất quán của trạng thái sức khỏe theo mốc thời gian và làm mượt dữ liệu (Smoothing bằng hàm Trung bình động).
