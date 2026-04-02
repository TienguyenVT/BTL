# IoMT Web Dashboard — Backend API Specification

**Base URL:** `http://localhost:8080/api`

**Database:** MongoDB (`iomt_health_monitor`)

**Date:** 2026-04-01

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Common Conventions](#3-common-conventions)
4. [API Endpoints](#4-api-endpoints)
   - [4.1 System](#41-system)
   - [4.2 Authentication](#42-authentication)
   - [4.3 Profile](#43-profile)
   - [4.4 Device](#44-device)
   - [4.5 Health Data](#45-health-data)
   - [4.6 Diary Notes](#46-diary-notes)
   - [4.7 Alerts](#47-alerts)
5. [Database Collections](#5-database-collections)
6. [CORS Configuration](#6-cors-configuration)
7. [Error Handling](#7-error-handling)
8. [Swagger UI](#8-swagger-ui)

---

## 1. Overview

IoMT Web Dashboard là REST API backend cho hệ thống giám sát sức khỏe IoT (Internet of Medical Things). Backend cung cấp các API cho:

- Xác thực người dùng (đăng ký / đăng nhập)
- Quản lý hồ sơ cá nhân & BMI
- Đăng ký thiết bị ESP32
- Đọc dữ liệu sức khỏe thời gian thực
- Ghi chép nhật ký sức khỏe cá nhân
- Nhận cảnh báo sức khỏe tự động

---

## 2. Architecture

```
Frontend (React / Vite)
    │
    │  HTTP + JSON
    ▼
Backend (Spring Boot 3.2.3)          ← Web Dashboard Java API
    │                                    Port: 8080
    │  MongoTemplate
    ▼
MongoDB (iomt_health_monitor)         ← Cùng DB với Python IoT Ingestion
    │
    ├── users            (AuthEntity)
    ├── profiles         (ProfileEntity)
    ├── devices          (DeviceEntity)
    ├── diary_notes      (DiaryNote)
    ├── alerts           (AlertEntity)
    └── realtime_health_data  (HealthData) ← Ghi bởi Python module
```

**Tech Stack:**

| Layer | Technology |
|---|---|
| Framework | Spring Boot 3.2.3 |
| Language | Java 21 |
| Database | MongoDB (via Spring Data MongoDB) |
| Build Tool | Maven Daemon (mvnd) |
| API Docs | SpringDoc OpenAPI (Swagger) |

---

## 3. Common Conventions

### 3.1 Authentication

Hiện tại **chưa có JWT**. Tất cả endpoint (trừ `/api/auth`) sử dụng header `X-User-Id` để xác định user.

```
X-User-Id: <user_id_from_login_response>
```

Nếu không gửi header, hệ thống tự động dùng user mặc định: `demo_user`

> **Lưu ý:** Password được lưu **plain text** (chỉ để demo). Cần thêm mã hóa & JWT token khi production.

### 3.2 Response Format

Không có response wrapper chung. Mỗi endpoint trả về data trực tiếp.

### 3.3 Content-Type

```
Content-Type: application/json
```

### 3.4 HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | OK — Thành công |
| 201 | Created — Tạo mới thành công |
| 204 | No Content — Xóa thành công |
| 400 | Bad Request — Dữ liệu đầu vào không hợp lệ |
| 401 | Unauthorized — Sai thông tin đăng nhập |
| 404 | Not Found — Resource không tồn tại |
| 409 | Conflict — Trùng lặp (email/MAC đã tồn tại) |

---

## 4. API Endpoints

---

### 4.1 System

#### `GET /api`

Health check — xác nhận backend đang chạy.

**Auth:** Không cần

**Response:**

```
Backend dang chay tai /api
```

---

### 4.2 Authentication

**Base Path:** `/api/auth`

> **Public — Không cần X-User-Id header**

---

#### `POST /api/auth/register`

Tạo tài khoản người dùng mới.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "yourpassword",
  "name": "Nguyen Van A"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| email | string | ✅ | Email (unique, định dạng email) |
| password | string | ✅ | Mật khẩu |
| name | string | ✅ | Tên hiển thị |

**Responses:**

| Status | Body |
|---|---|
| 201 | `{"id": "...", "name": "...", "message": "Dang ky thanh cong"}` |
| 400 | `{"message": "Email, password, name la bat buoc"}` |
| 409 | `{"message": "Email da ton tai"}` |

---

#### `POST /api/auth/login`

Đăng nhập.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| email | string | ✅ | Email |
| password | string | ✅ | Mật khẩu |

**Responses:**

| Status | Body |
|---|---|
| 200 | `{"id": "...", "name": "...", "message": "Dang nhap thanh cong"}` |
| 401 | `{"message": "Email khong ton tai"}` |
| 401 | `{"message": "Mat khau khong dung"}` |

**Sau khi đăng nhập thành công:** Lưu `id` (user ID) để gửi trong header `X-User-Id` cho các request tiếp theo.

---

### 4.3 Profile

**Base Path:** `/api/profile`

**Auth:** Header `X-User-Id` (mặc định: `demo_user`)

---

#### `GET /api/profile`

Lấy thông tin hồ sơ cá nhân. Tự động tạo profile mặc định nếu chưa có.

**Response:**

```json
{
  "userId": "demo_user",
  "age": 25,
  "height": 170.0,
  "weight": 65.0,
  "bmi": 22.5,
  "updatedAt": "2026-04-01T11:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| userId | string | ID người dùng |
| age | integer/null | Tuổi |
| height | number/null | Chiều cao (cm) |
| weight | number/null | Cân nặng (kg) |
| bmi | number/null | Chỉ số BMI (tính động) |
| updatedAt | datetime/null | Thời điểm cập nhật gần nhất |

**BMI Calculation:** `weight / (height/100)²` — chỉ tính khi cả height và weight đều có giá trị > 0.

---

#### `PUT /api/profile`

Cập nhật thông tin hồ sơ. Chỉ cập nhật trường được gửi (null fields bị bỏ qua).

**Request:**

```json
{
  "age": 26,
  "height": 172.0,
  "weight": 68.0
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| age | integer | ❌ | Tuổi mới |
| height | number | ❌ | Chiều cao mới (cm) |
| weight | number | ❌ | Cân nặng mới (kg) |

**Response:** Profile đã cập nhật (cùng format với GET).

---

### 4.4 Device

**Base Path:** `/api/devices`

**Auth:** Header `X-User-Id`

---

#### `POST /api/devices`

Đăng ký thiết bị ESP32 mới.

**Request:**

```json
{
  "macAddress": "AA:BB:CC:DD:EE:FF",
  "name": "ESP32-Bedroom"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| macAddress | string | ✅ | Địa chỉ MAC ESP32 (unique) |
| name | string | ❌ | Tên tùy ý cho thiết bị |

**Responses:**

| Status | Body |
|---|---|
| 201 | `{"id": "...", "macAddress": "...", "name": "...", "createdAt": "...", "message": "Them thiet bi thanh cong"}` |
| 400 | `{"message": "MAC Address la bat buoc"}` |
| 409 | `{"message": "MAC Address da ton tai"}` |

---

#### `GET /api/devices`

Lấy danh sách thiết bị đã đăng ký.

**Response:**

```json
[
  {
    "id": "...",
    "macAddress": "AA:BB:CC:DD:EE:FF",
    "name": "ESP32-Bedroom",
    "createdAt": "2026-04-01T11:00:00Z",
    "message": null
  }
]
```

---

#### `DELETE /api/devices/{id}`

Xóa thiết bị.

**Response:**

| Status | Body |
|---|---|
| 204 | (empty) |
| 404 | (empty) |

---

### 4.5 Health Data

**Base Path:** `/api/health`

**Auth:** Header `X-User-Id`

**Data Source:** Collection `realtime_health_data` — ghi bởi Python IoT Ingestion module. Backend chỉ đọc.

---

#### `GET /api/health/latest`

Lấy chỉ số sức khỏe mới nhất.

**Response:**

```json
{
  "id": "...",
  "userId": "demo_user",
  "deviceId": "AA:BB:CC:DD:EE:FF",
  "timestamp": "2026-04-01T11:00:00Z",
  "bpm": 72.0,
  "spo2": 98.0,
  "bodyTemp": 36.6,
  "gsrAdc": 512.0,
  "extTempC": 28.5,
  "extHumidityPct": 65.0,
  "label": "Normal",
  "timeSlot": "morning"
}
```

| Field | Type | Description |
|---|---|---|
| bpm | number | Nhịp tim (beats per minute) |
| spo2 | number | Độ bão hòa oxy (SpO2 %) |
| bodyTemp | number | Nhiệt độ cơ thể (°C) |
| gsrAdc | number | Giá trị GSR (galvanic skin response) |
| extTempC | number | Nhiệt độ môi trường (°C) |
| extHumidityPct | number | Độ ẩm môi trường (%) |
| label | string | Nhãn: "Normal" / "Stress" / "Fever" |
| timeSlot | string | Buổi: "morning" / "afternoon" / "evening" / "night" |

---

#### `GET /api/health/history`

Lấy dữ liệu trong khoảng N giờ gần đây.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| hours | integer | 24 | Số giờ lùi lại từ thời điểm hiện tại |

**Example:** `GET /api/health/history?hours=48`

**Response:** Array `[...]` sắp xếp từ cũ đến mới.

---

#### `GET /api/health/recent`

Lấy N bản ghi gần nhất.

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| limit | integer | 20 | Số bản ghi tối đa trả về |

**Example:** `GET /api/health/recent?limit=10`

**Response:** Array `[...]` sắp xếp từ mới đến cũ.

---

### 4.6 Diary Notes

**Base Path:** `/api/diary-notes`

**Auth:** Header `X-User-Id`

---

#### `POST /api/diary-notes`

Tạo ghi chú mới.

**Request:**

```json
{
  "title": "Bi quyet giam stress",
  "content": "Tap thoi quen ho hap deu, uong nuc nhieu..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| title | string | ✅ | Tiêu đề ghi chú |
| content | string | ✅ | Nội dung chi tiết |

**Response:** `201` — DiaryDto đã tạo (có `id` và `createdAt`).

---

#### `GET /api/diary-notes`

Lấy danh sách tất cả ghi chú (mới nhất trước).

**Response:** Array `[...]`

---

#### `GET /api/diary-notes/{id}`

Lấy chi tiết 1 ghi chú.

**Response:** `200` DiaryDto | `404`

---

#### `PUT /api/diary-notes/{id}`

Sửa ghi chú. Chỉ cập nhật trường được gửi (null fields bị bỏ qua).

**Request:**

```json
{
  "title": "Tieu de moi",
  "content": "Noi dung moi..."
}
```

**Response:** `200` DiaryDto đã cập nhật | `404`

---

#### `DELETE /api/diary-notes/{id}`

Xóa ghi chú.

**Response:** `204` | `404`

---

### 4.7 Alerts

**Base Path:** `/api/alerts`

**Auth:** Header `X-User-Id`

**Nguồn:** Alerts được tạo tự động bởi hệ thống AI/phân tích dữ liệu sức khỏe. Người dùng chỉ xem và xóa.

---

#### `GET /api/alerts`

Lấy danh sách tất cả cảnh báo (mới nhất trước).

**Response:**

```json
[
  {
    "id": "...",
    "label": "Stress",
    "message": "Muc do stress cao: BPM 95, GSR 820",
    "timestamp": "2026-04-01T10:30:00Z",
    "isRead": false
  },
  {
    "id": "...",
    "label": "Fever",
    "message": "Nhiet do co the cao: 38.2°C",
    "timestamp": "2026-04-01T09:15:00Z",
    "isRead": true
  }
]
```

| Field | Type | Description |
|---|---|---|
| label | string | Loại: `"Stress"` / `"Fever"` |
| message | string | Nội dung cảnh báo chi tiết |
| timestamp | datetime | Thời điểm cảnh báo được tạo |
| isRead | boolean | Đã đọc chưa |

---

#### `GET /api/alerts/count`

Đếm số cảnh báo chưa đọc.

**Response:**

```json
{
  "unreadCount": 3
}
```

---

#### `DELETE /api/alerts/{id}`

Xóa cảnh báo.

**Response:** `204` | `404`

---

## 5. Database Collections

| Collection | Entity | Description |
|---|---|---|
| `users` | AuthEntity | Tài khoản người dùng |
| `profiles` | ProfileEntity | Hồ sơ sinh lý (age, height, weight) |
| `devices` | DeviceEntity | Thiết bị ESP32 đã đăng ký |
| `diary_notes` | DiaryNote | Ghi chép nhật ký sức khỏe |
| `alerts` | AlertEntity | Cảnh báo sức khỏe tự động |
| `realtime_health_data` | HealthData | Dữ liệu sức khỏe (ghi bởi Python) |

---

## 6. CORS Configuration

Frontend có thể truy cập API từ các origin sau:

- `http://localhost:5173` (Vite)
- `http://localhost:5174` (Vite)
- `http://localhost:3000`

**Allowed methods:** GET, POST, PUT, DELETE, OPTIONS

**Allowed headers:** `*` (tất cả)

Nếu frontend chạy ở origin khác, cần thêm vào `DashboardApplication.java` dòng:

```java
.allowedOrigins("http://your-frontend-origin")
```

---

## 7. Error Handling

Tất cả error response có body là JSON với field `message`:

```json
{
  "message": "Mo ta loi"
}
```

**Common errors:**

| Message | HTTP Status | Nguyên nhân |
|---|---|---|
| `Email, password, name la bat buoc` | 400 | Thiếu field bắt buộc |
| `MAC Address la bat buoc` | 400 | Thiếu MAC khi đăng ký thiết bị |
| `Email da ton tai` | 409 | Email đã được đăng ký |
| `MAC Address da ton tai` | 409 | MAC đã được đăng ký |
| `Email khong ton tai` | 401 | Email chưa đăng ký |
| `Mat khau khong dung` | 401 | Sai mật khẩu |

---

## 8. Swagger UI

API documentation (Swagger) có sẵn tại:

```
http://localhost:8080/swagger-ui.html
```

**Lưu ý:** Cần bổ sung SpringDoc dependency vào `pom.xml` nếu chưa có.

```xml
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.3.0</version>
</dependency>
```

---

## 9. Quick Test Reference (PowerShell / CMD)

```bash
# Health check
curl http://localhost:8080/api

# Register
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"123","name":"Test"}'

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"123"}'

# Get profile (replace USER_ID)
curl http://localhost:8080/api/profile \
  -H "X-User-Id: <USER_ID>"

# Update profile
curl -X PUT http://localhost:8080/api/profile \
  -H "Content-Type: application/json" \
  -H "X-User-Id: <USER_ID>" \
  -d '{"age":25,"height":170,"weight":65}'

# Get latest health data
curl http://localhost:8080/api/health/latest \
  -H "X-User-Id: <USER_ID>"

# Get health history (last 24h)
curl "http://localhost:8080/api/health/history?hours=24" \
  -H "X-User-Id: <USER_ID>"

# Add device
curl -X POST http://localhost:8080/api/devices \
  -H "Content-Type: application/json" \
  -H "X-User-Id: <USER_ID>" \
  -d '{"macAddress":"AA:BB:CC:DD:EE:FF","name":"ESP32-1"}'

# List devices
curl http://localhost:8080/api/devices \
  -H "X-User-Id: <USER_ID>"

# Create diary note
curl -X POST http://localhost:8080/api/diary-notes \
  -H "Content-Type: application/json" \
  -H "X-User-Id: <USER_ID>" \
  -d '{"title":"Test","content":"Hello"}'

# Get diary notes
curl http://localhost:8080/api/diary-notes \
  -H "X-User-Id: <USER_ID>"

# Get alerts
curl http://localhost:8080/api/alerts \
  -H "X-User-Id: <USER_ID>"

# Count unread alerts
curl http://localhost:8080/api/alerts/count \
  -H "X-User-Id: <USER_ID>"
```
