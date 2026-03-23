# Hướng dẫn Test IoMT Dashboard API

## Mục lục
1. [Tổng quan](#1-tổng-quan)
2. [Import Collection vào Postman](#2-import-collection-vào-postman)
3. [Test thủ công từng bước](#3-test-thủ-công-từng-bước)
4. [Test tự động bằng Runner](#4-test-tự-động-bằng-runner)
5. [Các lỗi thường gặp](#5-các-lỗi-thường-gặp)

---

## 1. Tổng quan

| Thành phần | Công nghệ | Port |
|-----------|-----------|------|
| Backend (Java Spring Boot) | MongoDB, JWT | `8080` |
| Frontend (React) | Vite, TailwindCSS | `5173` |
| ESP32 (Python) | UART → REST API | — |
| API Base URL | — | `http://localhost:8080/api` |

**8 Module cần test:**

```
1. AUTH         → Register + Login
2. PROFILE      → Get + Update
3. DEVICE       → Create + List + Delete
4. DASHBOARD    → Get latest + Get by ID
5. HEALTH-HIST  → Paginated + Filter by date
6. ALERT        → List + Count + Delete
7. DIARY        → Create + List + Get + Update + Delete
```

**Thứ tự test bắt buộc:**

```
Bước 1: Register + Login (lấy JWT token)
   ↓
Bước 2: Profile, Device, Diary (test CRUD)
   ↓
Bước 3: Dashboard, HealthHistory, Alert (test đọc)
   ↓
Bước 4: Cleanup (xóa dữ liệu test)
```

---

## 2. Import Collection vào Postman

### Bước 2.1 — Mở Postman

1. Mở ứng dụng Postman
2. Click **Import** (góc trên bên trái)

### Bước 2.2 — Import file

```
Cách 1: Kéo thả file Postman.json vào Postman
Cách 2: Click "Upload Files" → chọn C:\Documents\BTL\Postman.json
Cách 3: Click "Link" → dán đường dẫn file
```

### Bước 2.3 — Kiểm tra import

Sau khi import thành công, bạn sẽ thấy collection **"IoMT Dashboard API"** trong sidebar bên trái với cấu trúc:

```
IoMT Dashboard API
├── 0. SYSTEM
│   └── GET / — Health check
├── 1. AUTH
│   ├── POST /auth/register
│   └── POST /auth/login
├── 2. PROFILE
│   ├── GET /profile
│   └── PUT /profile
├── 3. DEVICE
│   ├── POST /devices
│   ├── GET /devices
│   └── DELETE /devices/{id}
├── 4. DASHBOARD
│   ├── GET /dashboard
│   └── GET /dashboard/{id}
├── 5. HEALTH HISTORY
│   ├── GET /health-history (phân trang)
│   └── GET /health-history (lọc ngày)
├── 6. ALERT
│   ├── GET /alerts
│   ├── GET /alerts/count
│   └── DELETE /alerts/{id}
├── 7. DIARY
│   ├── POST /diary-notes
│   ├── GET /diary-notes
│   ├── GET /diary-notes/{id}
│   ├── PUT /diary-notes/{id}
│   └── DELETE /diary-notes/{id}
└── TEST SEQUENCE
    └── CHẠY TOÀN BỘ
```

### Bước 2.4 — Kiểm tra Variables

1. Click **IoMT Dashboard API** (tên collection)
2. Chuyển sang tab **Variables**
3. Đảm bảo các biến đã được khai báo:

| Variable | Initial Value | Current Value |
|----------|--------------|---------------|
| `baseUrl` | `http://localhost:8080/api` | `http://localhost:8080/api` |
| `userId` | *(để trống)* | *(tự động lưu)* |
| `authToken` | *(để trống)* | *(tự động lưu)* |
| `deviceId` | *(để trống)* | *(tự động lưu)* |
| `diaryNoteId` | *(để trống)* | *(tự động lưu)* |
| `alertId` | *(để trống)* | *(tự động lưu)* |
| `dashboardId` | *(để trống)* | *(tự động lưu)* |

### Bước 2.5 — Cấu hình Authorization cho toàn bộ Collection

1. Click **IoMT Dashboard API** (tên collection)
2. Chuyển sang tab **Authorization**
3. Cấu hình:

```
Type: Bearer Token
Token: {{authToken}}
```

4. Click **"Apply to all requests"** (nút bên dưới)

> **Lưu ý:** Những request không cần auth (health check, register, login) sẽ override bằng `Type: No Auth`.

---

## 3. Test thủ công từng bước

### Bước 0 — Khởi động Backend

Đảm bảo backend đang chạy:

```bash
cd C:\Documents\BTL\backend\web-dashboard
./mvnw spring-boot:run
```

Hoặc chạy bằng IDE (IntelliJ / VS Code).

### Bước 1 — Health Check

**Mục đích:** Kiểm tra backend có đang chạy không.

```
Trong Postman:
  1. Mở collection > 0. SYSTEM
  2. Click "GET / — Health check"
  3. Click "Send"

Kết quả mong đợi:
  Status: 200 OK
  Body: Thông điệp chào mừng
```

**Nếu lỗi `ECONNREFUSED`:**
→ Backend chưa chạy. Khởi động backend trước.

### Bước 2 — Đăng ký tài khoản

**Mục đích:** Tạo tài khoản test.

```
Trong Postman:
  1. Mở collection > 1. AUTH
  2. Click "POST /auth/register — Đăng ký tài khoản mới"
  3. (Tùy chọn) Sửa email trong Body để tránh trùng
  4. Click "Send"

Kết quả mong đợi:
  Status: 201 Created
  Body: { "id": "...", "email": "...", "name": "Nguyen Van A" }
  (Test script tự động lưu userId vào biến)
```

**Nếu lỗi 409 Conflict:**
→ Email đã tồn tại. Đổi email khác trong Body.

**Nếu lỗi 400 Bad Request:**
→ Thiếu trường bắt buộc. Kiểm tra Body JSON.

### Bước 3 — Đăng nhập

**Mục đích:** Lấy JWT token.

```
Trong Postman:
  1. Click "POST /auth/login — Đăng nhập"
  2. Dùng email + password đã đăng ký ở Bước 2
  3. Click "Send"

Kết quả mong đợi:
  Status: 200 OK
  Body: {
    "id": "...",
    "email": "test01@example.com",
    "name": "Nguyen Van A",
    "token": "eyJhbGciOiJIUzI1NiJ9..."
  }

  ⚠️ QUAN TRỌNG: Test script tự động lưu token vào {{authToken}}
  ⚠️ Kiểm tra tab "Variables" để xác nhận {{authToken}} đã có giá trị
```

**Kiểm tra biến đã lưu:**

```
1. Click tên Collection "IoMT Dashboard API"
2. Tab "Variables"
3. Dòng "authToken" → cột "CURRENT VALUE" phải có giá trị bắt đầu bằng "eyJ..."
```

### Bước 4 — Test các module (có Auth)

Sau khi có token, tất cả request bên dưới đều tự động gửi kèm `Authorization: Bearer {{authToken}}`.

#### 4.1 Profile — Xem thông tin cá nhân

```
1. Mở collection > 2. PROFILE
2. Click "GET /profile — Xem thông tin cá nhân"
3. Click "Send"

Kết quả:
  Status: 200 OK
  Body: Profile hiện tại (null fields nếu chưa cập nhật)
```

#### 4.2 Profile — Cập nhật thông tin

```
1. Click "PUT /profile — Cập nhật thông tin cá nhân"
2. Sửa Body nếu cần (tuổi, chiều cao, cân nặng)
3. Click "Send"

Kết quả:
  Status: 200 OK
  Body: Profile đã cập nhật (có BMI tính tự động)
```

#### 4.3 Device — Thêm thiết bị

```
1. Mở collection > 3. DEVICE
2. Click "POST /devices — Thêm thiết bị mới"
3. (Tùy chọn) Đổi MAC address để tránh trùng
4. Click "Send"

Kết quả:
  Status: 201 Created
  (Test script tự động lưu deviceId vào biến)
```

#### 4.4 Device — Xem danh sách

```
1. Click "GET /devices — Danh sách thiết bị"
2. Click "Send"

Kết quả:
  Status: 200 OK
  Body: Array chứa thiết bị vừa tạo
```

#### 4.5 Diary — Tạo ghi chú

```
1. Mở collection > 7. DIARY
2. Click "POST /diary-notes — Tạo ghi chú mới"
3. Sửa title + content nếu cần
4. Click "Send"

Kết quả:
  Status: 201 Created
  (Test script tự động lưu diaryNoteId vào biến)
```

#### 4.6 Diary — Xem danh sách

```
1. Click "GET /diary-notes — Danh sách ghi chú"
2. Click "Send"

Kết quả:
  Status: 200 OK
  Body: Array chứa ghi chú vừa tạo
```

#### 4.7 Diary — Sửa ghi chú

```
1. Click "PUT /diary-notes/{id} — Sửa ghi chú"
2. Sửa nội dung trong Body
3. Click "Send"

Kết quả:
  Status: 200 OK
  Body: Ghi chú đã được cập nhật
```

#### 4.8 Diary — Xóa ghi chú

```
1. Click "DELETE /diary-notes/{id} — Xóa ghi chú"
2. Click "Send"

Kết quả:
  Status: 204 No Content
```

#### 4.9 Device — Xóa thiết bị

```
1. Click "DELETE /devices/{id} — Xóa thiết bị"
2. Click "Send"

Kết quả:
  Status: 204 No Content
```

### Bước 5 — Dashboard & Health History

> **Lưu ý:** Những endpoint này cần có dữ liệu sức khỏe trong MongoDB.
> Nếu chưa có, Python IoT module chưa gửi dữ liệu → response sẽ là `null`.

```
1. Mở collection > 4. DASHBOARD
2. Click "GET /dashboard — Chỉ số mới nhất"
3. Click "Send"

Kết quả A (có dữ liệu):
  Status: 200 OK
  Body: { bpm, spo2, bodyTemp, label, timestamp, ... }

Kết quả B (chưa có dữ liệu):
  Status: 200 OK
  Body: null
  → Bình thường, cần Python module gửi dữ liệu trước
```

---

## 4. Test tự động bằng Runner

Postman Collection Runner cho phép chạy tất cả request theo thứ tự tự động.

### Bước 4.1 — Mở Runner

```
Cách 1: Phím tắt: Ctrl + Shift + R (Windows)
Cách 2: Click nút "Runner" trong Postman (góc trên bên phải)
```

### Bước 4.2 — Cấu hình Runner

Trong cửa sổ Runner:

```
1. Collection: Chọn "IoMT Dashboard API"
2. Environment: Chọn "No Environment" (hoặc tạo mới)
3. Iterations: 1 (chạy 1 lần)
4. Delay: 0ms (không delay giữa các request)
5. Keep variable values: ✅ Tích (giữ lại biến đã lưu)
```

### Bước 4.3 — Chạy

```
1. Click "Run IoMT Dashboard API"
2. Quan sát kết quả:
   - ✅ PASSED: Request thành công, test script pass
   - ❌ FAILED: Request lỗi hoặc test script fail

3. Kiểm tra tổng quan:
   - Tổng số request: 18
   - Passed: Xem cột Status
   - Failed: Xem cột Failures
```

### Bước 4.4 — Kiểm tra biến sau khi chạy

```
1. Quay lại Collection
2. Tab "Variables"
3. Kiểm tra cột "CURRENT VALUE":
   - authToken: phải có giá trị
   - userId: phải có giá trị
   - deviceId: có thể trống (đã xóa)
   - diaryNoteId: có thể trống (đã xóa)
```

---

## 5. Các lỗi thường gặp

### Lỗi `401 Unauthorized`

**Nguyên nhân:** Token hết hạn hoặc chưa có token.

**Khắc phục:**
```
1. Chạy lại POST /auth/login để lấy token mới
2. Kiểm tra tab Variables > authToken đã có giá trị chưa
3. Kiểm tra Authorization đã Apply to all requests chưa
```

### Lỗi `403 Forbidden`

**Nguyên nhân:** Spring Security chặn endpoint.

**Khắc phục:**
```
1. Kiểm tra SecurityConfig.java — endpoint đó có được permitAll() không
2. Kiểm tra JwtAuthFilter — filter có hoạt động đúng không
3. Kiểm tra token có đúng định dạng không (bắt đầu bằng "eyJ...")
```

### Lỗi `409 Conflict` (Device/Register)

**Nguyên nhân:** Email hoặc MAC address đã tồn tại.

**Khắc phục:**
```
1. Đổi email trong Body (VD: test02@example.com)
2. Đổi MAC address trong Body (VD: BB:CC:DD:EE:FF:02)
```

### Lỗi `ECONNREFUSED`

**Nguyên nhân:** Backend không chạy.

**Khắc phục:**
```
1. Khởi động backend:
   cd C:\Documents\BTL\backend\web-dashboard
   ./mvnw spring-boot:run

2. Kiểm tra port 8080 có đang bị chiếm không:
   netstat -ano | findstr :8080

3. Đổi port trong application.properties nếu cần
```

### Lỗi `404 Not Found`

**Nguyên nhân:**
- Endpoint chưa implement
- Sai đường dẫn URL
- Collection Variable chưa lưu ID

**Khắc phục:**
```
1. Kiểm tra URL trong Postman có đúng không
   (VD: /diary-notes hay /diary/notes?)
2. Chạy GET / trước để xem backend liệt kê các endpoint
3. Chạy GET /devices trước để lấy deviceId hợp lệ
```

### Lỗi `500 Internal Server Error`

**Nguyên nhân:** Lỗi phía server (code Java).

**Khắc phục:**
```
1. Kiểm tra console/log của backend (IntelliJ terminal)
2. Kiểm tra MongoDB có đang chạy không
3. Kiểm tra kết nối MongoDB trong application.properties
```

### Response body `null` (Dashboard/HealthHistory)

**Nguyên nhân:** Chưa có dữ liệu sức khỏe trong MongoDB.

**Giải thích:** Đây là hành vi BÌNH THƯỜNG, không phải lỗi.
- ESP32 Python module chưa gửi dữ liệu lên
- Cần khởi động Python script để gửi dữ liệu test

**Cách gửi dữ liệu test thủ công (bỏ qua ESP32):**

```bash
# Giả lập dữ liệu sức khỏe bằng curl
curl -X POST http://localhost:8080/api/health-data \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "{{userId}}",
    "bpm": 75.0,
    "spo2": 98.5,
    "bodyTemp": 36.8,
    "gsrAdc": 512
  }'
```

---

## Checklist Test

```
□ Backend đang chạy (port 8080)
□ MongoDB đang chạy (port 27017)
□ Postman.json đã import thành công
□ Variables đã khai báo đầy đủ
□ Authorization đã Apply to all requests
□ Đăng ký tài khoản (201 Created)
□ Đăng nhập lấy token (200 OK, token lưu vào biến)
□ GET /profile (200 OK)
□ PUT /profile (200 OK, BMI tính đúng)
□ POST /devices (201 Created, deviceId lưu)
□ GET /devices (200 OK)
□ POST /diary-notes (201 Created, diaryNoteId lưu)
□ GET /diary-notes (200 OK)
□ PUT /diary-notes (200 OK)
□ GET /diary-notes/{id} (200 OK)
□ DELETE /diary-notes/{id} (204 No Content)
□ DELETE /devices/{id} (204 No Content)
□ GET /dashboard (200 OK, null hoặc có dữ liệu)
□ GET /health-history (200 OK)
□ GET /alerts (200 OK)
□ Runner: Tất cả request PASSED
```
