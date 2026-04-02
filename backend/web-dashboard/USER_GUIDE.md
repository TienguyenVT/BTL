# IoMT Web Dashboard — Hướng Dẫn Sử Dụng Backend

**Cho người dùng cuối & lập trình viên frontend**

---

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Cách khởi động Backend](#2-cách-khởi-động-backend)
3. [Đăng ký & Đăng nhập](#3-đăng-ký--đăng-nhập)
4. [Quản lý Hồ sơ cá nhân](#4-quản-lý-hồ-sơ-cá-nhân)
5. [Đăng ký Thiết bị ESP32](#5-đăng-ký-thiết-bị-esp32)
6. [Xem Dữ liệu Sức khỏe](#6-xem-dữ-liệu-sức-khỏe)
7. [Nhật ký Sức khỏe](#7-nhật-ký-sức-khỏe)
8. [Cảnh báo Sức khỏe](#8-cảnh-báo-sức-khỏe)
9. [Cách kết nối Frontend](#9-cách-kết-nối-frontend)
10. [Giải đáp thắc mắc](#10-giải-đáp-thắc-mắc)

---

## 1. Tổng quan hệ thống

IoMT Web Dashboard gồm 3 phần chính:

```
ESP32 (Cảm biến) ──→ Python IoT Ingestion ──→ MongoDB
                                                    │
                                           Backend Java API (8080)
                                                    │
                                           Frontend React (5173)
```

| Thành phần | Port | Mô tả |
|---|---|---|
| Backend Java | 8080 | REST API |
| MongoDB | 27017 | Lưu trữ dữ liệu |
| Frontend | 5173 | Giao diện người dùng (nếu có) |

---

## 2. Cách khởi động Backend

### Yêu cầu

- Java 21+
- Maven Daemon (mvnd) hoặc Maven (mvn)
- MongoDB đang chạy tại `localhost:27017`

### Dùng Maven Daemon (mvnd) 

```cmd
cd C:\Documents\BTL\backend\web-dashboard
mvnd spring-boot:run
```


### Kiểm tra Backend đã chạy

Mở trình duyệt truy cập:

```
http://localhost:8080/api
```

Nếu thấy dòng chữ `Backend dang chay tai /api` — Backend đang hoạt động bình thường.

---

## 3. Đăng ký & Đăng nhập

### 3.1 Đăng ký tài khoản

**POST** `http://localhost:8080/api/auth/register`

**Request body (JSON):**

```json
{
  "email": "nguyenvana@email.com",
  "password": "matkhau123",
  "name": "Nguyen Van A"
}
```

**Kết quả thành công (201):**

```json
{
  "id": "69cca34a39a8ac2e3739be4e",
  "name": "Nguyen Van A",
  "message": "Dang ky thanh cong"
}
```

> **Lưu lại `id`** — đây là User ID dùng cho các request tiếp theo.

**Các lỗi có thể:**

| Lỗi | Nguyên nhân |
|---|---|
| 400: "Email, password, name la bat buoc" | Thiếu thông tin bắt buộc |
| 409: "Email da ton tai" | Email đã được đăng ký |

---

### 3.2 Đăng nhập

**POST** `http://localhost:8080/api/auth/login`

**Request body (JSON):**

```json
{
  "email": "nguyenvana@email.com",
  "password": "matkhau123"
}
```

**Kết quả thành công (200):**

```json
{
  "id": "69cca34a39a8ac2e3739be4e",
  "name": "Nguyen Van A",
  "message": "Dang nhap thanh cong"
}
```

---

## 4. Quản lý Hồ sơ cá nhân

### 4.1 Xem hồ sơ

**GET** `http://localhost:8080/api/profile`

**Header cần gửi:**
```
X-User-Id: <user_id_của_bạn>
```

**Response:**

```json
{
  "userId": "69cca34a39a8ac2e3739be4e",
  "age": 25,
  "height": 170.0,
  "weight": 65.0,
  "bmi": 22.5,
  "updatedAt": "2026-04-01T11:00:00Z"
}
```

> **BMI** được tính tự động từ chiều cao và cân nặng. Nếu chưa có thông tin, BMI sẽ là `null`.

---

### 4.2 Cập nhật hồ sơ

**PUT** `http://localhost:8080/api/profile`

**Header:** `X-User-Id: <user_id>`

**Request body (chỉ gửi trường muốn cập nhật):**

```json
{
  "age": 26,
  "height": 172.0,
  "weight": 68.0
}
```

**Giải thích BMI:**

| BMI | Phân loại |
|---|---|
| < 18.5 | Thiếu cân |
| 18.5 – 24.9 | Bình thường |
| 25 – 29.9 | Thừa cân |
| >= 30 | Béo phì |

---

## 5. Đăng ký Thiết bị ESP32

### 5.1 Thêm thiết bị

**POST** `http://localhost:8080/api/devices`

**Header:** `X-User-Id: <user_id>`

**Request body:**

```json
{
  "macAddress": "AA:BB:CC:DD:EE:FF",
  "name": "ESP32-Phòng ngủ"
}
```

- **macAddress** là bắt buộc — địa chỉ MAC của ESP32
- **name** là tùy chọn — đặt tên dễ nhớ cho thiết bị

---

### 5.2 Xem danh sách thiết bị

**GET** `http://localhost:8080/api/devices`

**Header:** `X-User-Id: <user_id>`

---

### 5.3 Xóa thiết bị

**DELETE** `http://localhost:8080/api/devices/<device_id>`

**Header:** `X-User-Id: <user_id>`

---

## 6. Xem Dữ liệu Sức khỏe

> **Nguồn dữ liệu:** Dữ liệu được gửi từ ESP32 qua Python IoT Ingestion module vào MongoDB. Backend chỉ đọc, không ghi.

### 6.1 Chỉ số mới nhất (Dashboard)

**GET** `http://localhost:8080/api/health/latest`

**Header:** `X-User-Id: <user_id>`

**Các chỉ số có trong response:**

| Chỉ số | Mô tả | Giá trị bình thường |
|---|---|---|
| bpm | Nhịp tim | 60–100 bpm |
| spo2 | Độ bão hòa oxy | 95–100% |
| bodyTemp | Nhiệt độ cơ thể | 36.1–37.2°C |
| gsrAdc | Phản ứng da điện | Thay đổi theo stress |
| extTempC | Nhiệt độ môi trường | Thay đổi |
| extHumidityPct | Độ ẩm môi trường | 30–60% |
| label | Nhãn: Normal/Stress/Fever | — |
| timeSlot | Buổi: morning/afternoon/evening/night | — |

---

### 6.2 Lịch sử theo thời gian

**GET** `http://localhost:8080/api/health/history?hours=24`

**Header:** `X-User-Id: <user_id>`

Lấy dữ liệu trong **N giờ** gần nhất. Mặc định: 24 giờ.

**Ví dụ:**
- `?hours=6` — 6 giờ gần đây
- `?hours=24` — 24 giờ gần đây
- `?hours=168` — 1 tuần gần đây

---

### 6.3 N bản ghi gần nhất

**GET** `http://localhost:8080/api/health/recent?limit=20`

**Header:** `X-User-Id: <user_id>`

Lấy **N bản ghi** mới nhất. Mặc định: 20 bản ghi.

---

## 7. Nhật ký Sức khỏe

### 7.1 Tạo ghi chú mới

**POST** `http://localhost:8080/api/diary-notes`

**Header:** `X-User-Id: <user_id>`

**Request body:**

```json
{
  "title": "Bi quyet giam stress",
  "content": "Tap thoi quen ho hap deu 5 phut/ngay, uong 2 lit nuoc, ngu du 7 gio"
}
```

---

### 7.2 Xem danh sách ghi chú

**GET** `http://localhost:8080/api/diary-notes`

**Header:** `X-User-Id: <user_id>`

Danh sách được sắp xếp từ **mới nhất đến cũ**.

---

### 7.3 Xem chi tiết 1 ghi chú

**GET** `http://localhost:8080/api/diary-notes/<id>`

**Header:** `X-User-Id: <user_id>`

---

### 7.4 Sửa ghi chú

**PUT** `http://localhost:8080/api/diary-notes/<id>`

**Header:** `X-User-Id: <user_id>`

**Request body:**

```json
{
  "title": "Tieu de moi",
  "content": "Noi dung da cap nhat"
}
```

Chỉ cần gửi trường muốn sửa, trường không gửi sẽ giữ nguyên.

---

### 7.5 Xóa ghi chú

**DELETE** `http://localhost:8080/api/diary-notes/<id>`

**Header:** `X-User-Id: <user_id>`

---

## 8. Cảnh báo Sức khỏe

> **Nguồn:** Cảnh báo được tạo **tự động** bởi hệ thống AI phân tích dữ liệu sức khỏe. Người dùng **chỉ xem và xóa**, không tạo thủ công.

### 8.1 Xem tất cả cảnh báo

**GET** `http://localhost:8080/api/alerts`

**Header:** `X-User-Id: <user_id>`

**Response:**

```json
[
  {
    "id": "abc123",
    "label": "Stress",
    "message": "Muc do stress cao: BPM 95, GSR 820",
    "timestamp": "2026-04-01T10:30:00Z",
    "isRead": false
  }
]
```

- **label "Stress"** — Mức độ căng thẳng cao (nhịp tim + GSR bất thường)
- **label "Fever"** — Sốt (nhiệt độ cơ thể > 37.5°C)

---

### 8.2 Đếm cảnh báo chưa đọc

**GET** `http://localhost:8080/api/alerts/count`

**Header:** `X-User-Id: <user_id>`

**Response:**

```json
{
  "unreadCount": 3
}
```

---

### 8.3 Xóa cảnh báo

**DELETE** `http://localhost:8080/api/alerts/<id>`

**Header:** `X-User-Id: <user_id>`

---

## 9. Cách kết nối Frontend

### 9.1 Base URL

Trong code frontend, khai báo:

```typescript
const API_BASE = "http://localhost:8080/api";
```

### 9.2 Luồng đăng nhập (khuyến nghị)

```typescript
// 1. Đăng nhập
const res = await fetch(`${API_BASE}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
const data = await res.json();

// 2. Lưu userId để dùng cho các request tiếp theo
localStorage.setItem("userId", data.id);

// 3. Gửi userId trong header cho mọi request
const userId = localStorage.getItem("userId");
fetch(`${API_BASE}/profile`, {
  headers: { "X-User-Id": userId },
});
```

### 9.3 Ví dụ: Lấy dữ liệu sức khỏe

```typescript
const userId = localStorage.getItem("userId");

// Chỉ số mới nhất
const latestRes = await fetch(`${API_BASE}/health/latest`, {
  headers: { "X-User-Id": userId },
});
const latestHealth = await latestRes.json();

// Lịch sử 24 giờ
const historyRes = await fetch(`${API_BASE}/health/history?hours=24`, {
  headers: { "X-User-Id": userId },
});
const history = await historyRes.json();
```

### 9.4 Frontend origins được phép

Backend cho phép frontend từ:

- `http://localhost:5173`
- `http://localhost:5174`
- `http://localhost:3000`

Nếu frontend chạy ở port khác, cần thêm vào `DashboardApplication.java`.

---

## 10. Giải đáp thắc mắc

### Q: Tôi không gửi header `X-User-Id` có sao không?

**A:** Không sao. Backend mặc định dùng user `demo_user` nếu không gửi header. Tuy nhiên, dữ liệu của bạn sẽ bị gộp chung với user khác cũng dùng `demo_user`. **Khuyến nghị luôn gửi header đúng User ID sau khi đăng nhập.**

---

### Q: Backend có hỗ trợ JWT token không?

**A:** **Chưa có.** Hiện tại dùng `X-User-Id` header đơn giản. Đây chỉ là bước demo. Cần thêm JWT authentication khi triển khai production.

---

### Q: Password có được mã hóa không?

**A:** **Chưa.** Password được lưu plain text trong MongoDB. Cần thêm BCrypt hoặc Argon2 hashing khi triển khai production.

---

### Q: MongoDB đang chạy ở port khác, không phải 27017?

**A:** Sửa file `src/main/resources/application.yml`, thay `mongodb://localhost:27017/iomt_health_monitor` thành URI của bạn.

---

### Q: Frontend bị lỗi CORS khi gọi API?

**A:** Kiểm tra origin của frontend có trong danh sách CORS ở `DashboardApplication.java` không. Nếu không, thêm vào.

---

### Q: Làm sao xem tài liệu API dạng Swagger?

**A:** Sau khi thêm SpringDoc dependency vào `pom.xml`, truy cập:

```
http://localhost:8080/swagger-ui.html
```

---

### Q: Dữ liệu health data không có?

**A:** Backend chỉ đọc dữ liệu từ collection `realtime_health_data`. Dữ liệu này do **Python IoT Ingestion module** ghi vào. Cần chạy Python module (port 8000) để thu thập dữ liệu từ ESP32 trước.

---

### Q: Tôi cần restart Backend mỗi lần sửa code?

**A:** Có, trừ khi dùng **Spring DevTools** (đã bật sẵn). DevTools hỗ trợ auto-restart khi file Java thay đổi. Chỉ cần refresh trình duyệt, không cần restart thủ công.

---

### Q: Backend có miễn phí không?

**A:** Hoàn toàn miễn phí. Tech stack: Spring Boot, Spring Data MongoDB, Maven — đều là open-source.
