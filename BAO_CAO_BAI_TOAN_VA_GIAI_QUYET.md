# BÁO CÁO: BÀI TOÁN VÀ CÁCH GIẢI QUYẾT
## Hệ thống Giám sát Sức khỏe IoMT - Web Dashboard

---

## 1. TỔNG QUAN DỰ ÁN

### 1.1 Giới thiệu
Dự án **IoMT Health Monitoring System** là hệ thống giám sát sức khỏe từ xa sử dụng thiết bị IoT (ESP32) kết hợp trí tuệ nhân tạo (AI) để dự đoán tình trạng sức khỏe của người dùng.

### 1.2 Công nghệ sử dụng

| Thành phần | Công nghệ | Mục đích |
|-----------|-----------|----------|
| Backend Web | Java Spring Boot 3.2.3 | REST API cho Dashboard |
| Database | MongoDB | Lưu trữ dữ liệu |
| Backend IoT | Python FastAPI | Nhận dữ liệu cảm biến + ML |
| ML Model | Python scikit-learn | Dự đoán: Normal/Stress/Fever |
| Thiết bị | ESP32 + DHT11 + MAX30102 | Thu thập dữ liệu sinh lý |
| Frontend | React/Vite | Giao diện người dùng |

### 1.3 Kiến trúc hệ thống

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  ESP32      │────▶│  Python      │────▶│  MongoDB        │
│  (Cảm biến) │     │  FastAPI     │     │  - users        │
│             │     │  (ML Model)  │     │  - devices      │
└─────────────┘     └──────────────┘     │  - profiles     │
                                         │  - alerts       │
┌─────────────┐     ┌──────────────┐     │  - diary_notes  │
│  Web         │◀───▶│  Java         │◀───▶│  - realtime     │
│  Dashboard   │     │  Spring Boot │     │    _health_data │
│  (React)     │     │  (8080)      │     └─────────────────┘
└─────────────┘     └──────────────┘
```

---

## 2. MÔ TẢ 8 USECASE

### 2.1 Danh sách 8 Usecase

| # | Usecase | Mô tả | Controller |
|---|---------|-------|------------|
| 1 | Đăng ký / Đăng nhập | Tạo tài khoản và đăng nhập người dùng | AuthController |
| 2 | Quản lý Hồ sơ | Xem và cập nhật thông tin sức khỏe cá nhân (tuổi, chiều cao, cân nặng, BMI) | ProfileController |
| 3 | Quản lý Thiết bị | Thêm, xem, xóa thiết bị ESP32 theo MAC Address | DeviceController |
| 4 | Dữ liệu Sức khỏe (Dashboard) | Hiển thị chỉ số sức khỏe mới nhất + lịch sử | HealthController |
| 6 | Cảnh báo | Xem và xóa cảnh báo sức khỏe từ AI | AlertController |
| 7 | Nhật ký Sức khỏe | CRUD đầy đủ nhật ký sức khỏe cá nhân | DiaryController |
| 8 | Dữ liệu Sức khỏe | API đọc dữ liệu sức khỏe (mới nhất, gần đây, theo giờ) | HealthController |

### 2.2 Chi tiết từng Usecase

#### Usecase 1: Đăng ký / Đăng nhập (Auth)
- **POST /api/auth/register**: Tạo tài khoản mới
  - Input: `{ email, password, name }`
  - Output: `{ id, name, message }`
  - Logic: Kiểm tra email đã tồn tại chưa → Lưu vào collection `users`

- **POST /api/auth/login**: Đăng nhập
  - Input: `{ email, password }`
  - Output: `{ id, name, message }`
  - Logic: Tìm email + kiểm tra password → Trả về thông tin user

#### Usecase 2: Quản lý Hồ sơ (Profile)
- **GET /api/profile**: Xem hồ sơ + BMI động
  - Logic: Tìm profile theo userId → Tạo mặc định nếu chưa có → Tính BMI
  - BMI = weight / (height/100)²

- **PUT /api/profile**: Cập nhật hồ sơ
  - Input: `{ age, height, weight }`
  - Logic: Chỉ cập nhật các trường khác null

#### Usecase 3: Quản lý Thiết bị (Device)
- **POST /api/devices**: Thêm thiết bị mới
  - Input: `{ macAddress, name }`
  - Logic: Kiểm tra MAC đã tồn tại chưa → Lưu vào collection `devices`

- **GET /api/devices**: Danh sách thiết bị của user

- **DELETE /api/devices/{id}**: Xóa thiết bị

#### Usecase 4: Dữ liệu Sức khỏe (Health - Dashboard)
- **GET /api/health/latest**: Lấy chỉ số mới nhất
  - Logic: Query `timestamp DESC`, limit 1
- **GET /api/health/history**: Dữ liệu N giờ gần đây
  - Params: `hours` (default: 24)
  - Logic: Lọc theo timestamp >= now - hours
- **GET /api/health/recent**: N bản ghi gần nhất
  - Params: `limit` (default: 20)

> **Lưu ý:** `DashboardController` và `HealthHistoryController` đã bị xóa (dead code) - chức năng tương ứng được gộp vào `HealthController`.

#### Usecase 6: Cảnh báo (Alert)
- **GET /api/alerts**: Danh sách cảnh báo
- **GET /api/alerts/count**: Đếm cảnh báo chưa đọc
- **DELETE /api/alerts/{id}**: Xóa cảnh báo

#### Usecase 7: Nhật ký Sức khỏe (Diary)
- **POST /api/diary-notes**: Tạo ghi chú
- **GET /api/diary-notes**: Danh sách (mới nhất trước)
- **GET /api/diary-notes/{id}**: Chi tiết
- **PUT /api/diary-notes/{id}**: Sửa (chỉ cập nhật trường khác null)
- **DELETE /api/diary-notes/{id}**: Xóa

---

## 3. CÁC VẤN ĐỀ GẶP PHẢI VÀ CÁCH GIẢI QUYẾT

### 3.1 Vấn đề 1: Quá phức tạp cho sinh viên mới học Java

#### Bài toán ban đầu (thiết kế quá nặng):
```
├── config/
│   ├── JwtAuthFilter.java        (JWT Filter phức tạp)
│   ├── JwtTokenProvider.java     (Tạo + verify token)
│   └── SecurityConfig.java       (Cấu hình Spring Security)
├── components/
│   ├── auth/
│   │   ├── AuthController.java   (commented out)
│   │   ├── AuthService.java      (logic skeleton)
│   │   ├── AuthEntity.java
│   │   └── AuthDto.java
│   ├── dashboard/                 (tương tự)
│   ├── device/
│   ├── profile/
│   ├── alert/
│   └── healthhistory/
```

**Vấn đề:**
- JWT Filter cần hiểu về filter chain, SecurityContext, ThreadLocal
- BCrypt cần hiểu về hashing, salt, encoding
- Service layer riêng biệt tăng số lượng file
- SecurityConfig cần hiểu Spring Security DSL
- Quá nhiều khái niệm cần học cùng lúc

#### Cách giải quyết: Đơn giản hóa tối đa

**Nguyên tắc thiết kế mới:**
1. **Không JWT/BCrypt**: Dùng `X-User-Id` header đơn giản
2. **UserUtils**: Lớp utility dùng chung trong `common/`, trích xuất userId với fallback
3. **Không Service layer riêng**: Logic nghiệp vụ trong Controller hoặc inline methods
4. **Không SecurityConfig**: Spring Boot permit all mặc định
5. **Password plain text**: Chỉ để demo, không bảo mật
6. **Constructor injection**: Dùng `@RequiredArgsConstructor` (không `@Autowired` field)
7. **Entity + Dto**: Mỗi component có Entity (MongoDB) và Dto (API response)

**Kết quả:**
```
├── DashboardApplication.java          # Entry point + CORS config
├── common/
│   └── UserUtils.java                ← User ID extraction utility
└── components/
    ├── auth/                         ← Usecase 1: Đăng ký / Đăng nhập
    │   ├── AuthController.java       (POST /register, POST /login)
    │   ├── AuthEntity.java
    │   └── AuthDto.java
    ├── profile/                      ← Usecase 2: Quản lý Hồ sơ
    │   ├── ProfileController.java   (GET /profile, PUT /profile)
    │   ├── ProfileEntity.java
    │   └── ProfileDto.java
    ├── device/                       ← Usecase 3: Quản lý Thiết bị
    │   ├── DeviceController.java    (POST/GET/DELETE /devices)
    │   ├── DeviceEntity.java
    │   └── DeviceDto.java
    ├── health/                       ← Usecase 4: Dashboard + Health History
    │   └── HealthController.java    (GET /health/latest, /history, /recent)
    ├── alert/                        ← Usecase 6: Cảnh báo
    │   ├── AlertController.java     (GET /alerts, GET /alerts/count, DELETE)
    │   ├── AlertEntity.java
    │   └── AlertDto.java
    ├── diary/                        ← Usecase 7: Nhật ký Sức khỏe
    │   ├── DiaryController.java     (POST/GET/PUT/DELETE /diary-notes)
    │   ├── DiaryNote.java
    │   └── DiaryDto.java
    └── system/                       ← Health check
        └── SystemController.java    (GET /api)
```

---

### 3.2 Vấn đề 2: Xác thực người dùng - JWT hay đơn giản?

#### Bài toán:
Làm sao để xác định user đang gọi API? JWT là chuẩn công nghiệp nhưng:
- Cần tạo token khi đăng nhập
- Cần verify token ở mỗi request
- Cần refresh token
- Cần lưu secret key
- Quá phức tạp cho sinh viên mới

#### Cách giải quyết: Header đơn giản `X-User-Id`

```java
// Thay vì JWT, chỉ cần đọc header
@GetMapping
public ResponseEntity<List<DiaryDto>> getAll(
        @RequestHeader(value = "X-User-Id", required = false) String userId) {
    String uid = (userId != null && !userId.isBlank()) ? userId : "demo_user";
    return ResponseEntity.ok(getAll(uid));
}
```

**Ưu điểm:**
- Đơn giản, dễ hiểu
- Không cần tạo token
- Frontend chỉ cần lưu userId từ đăng nhập

**Nhược điểm (chấp nhận cho mục đích học):**
- Không bảo mật (ai biết userId có thể truy cập)
- Không mã hóa
- Không có thời hạn

---

### 3.3 Vấn đề 3: Kết nối MongoDB với Spring Boot

#### Bài toán:
Sinh viên mới học Java chưa quen với:
- `@Document` annotation
- `@Field` annotation (ánh xạ field name)
- `MongoTemplate`
- `Query` và `Criteria`
- Repository vs Template

#### Cách giải quyết: Học qua ví dụ cụ thể

**Pattern cơ bản (tham khảo DiaryController):**

```java
// 1. Định nghĩa Entity với @Document và @Field
@Document(collection = "diary_notes")
public class DiaryNote {
    @Id private String id;
    @Field("user_id") private String userId;
    @Field("title") private String title;
}

// 2. Sử dụng MongoTemplate với Query + Criteria
@RestController
@RequiredArgsConstructor
public class DiaryController {
    private final MongoTemplate mongoTemplate;

    // Tìm tất cả theo điều kiện
    @GetMapping
    public List<DiaryDto> getAll(@RequestHeader("X-User-Id") String userId) {
        Query query = new Query(
            Criteria.where("user_id").is(userId)
        ).with(Sort.by(Direction.DESC, "created_at"));

        return mongoTemplate.find(query, DiaryNote.class)
                .stream()
                .map(DiaryDto::fromEntity)
                .toList();
    }

    // Tìm 1 bản ghi
    @GetMapping("/{id}")
    public ResponseEntity<DiaryDto> getById(@PathVariable String id) {
        Query query = new Query(Criteria.where("_id").is(id));
        DiaryNote note = mongoTemplate.findOne(query, DiaryNote.class);
        // ...
    }

    // Lưu mới
    @PostMapping
    public DiaryDto create(@RequestBody DiaryDto dto) {
        DiaryNote note = dto.toEntity(userId);
        DiaryNote saved = mongoTemplate.save(note);
        return DiaryDto.fromEntity(saved);
    }

    // Xóa
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable String id) {
        Query query = new Query(Criteria.where("_id").is(id));
        DiaryNote note = mongoTemplate.findOne(query, DiaryNote.class);
        mongoTemplate.remove(note);
        return ResponseEntity.noContent().build();
    }
}
```

**Các Query Criteria thường dùng:**

| MongoDB Query | Java Code |
|---------------|-----------|
| `field = value` | `Criteria.where("field").is(value)` |
| `field > value` | `Criteria.where("field").gt(value)` |
| `field >= value` | `Criteria.where("field").gte(value)` |
| `field < value` | `Criteria.where("field").lt(value)` |
| `field <= value` | `Criteria.where("field").lte(value)` |
| Kết hợp AND | `.and("field2").is(value2)` |
| Lấy 1 bản ghi | `mongoTemplate.findOne(query, Entity.class)` |
| Đếm | `mongoTemplate.count(query, Entity.class)` |

---

### 3.4 Vấn đề 4: Tính BMI động hay lưu vào database?

#### Bài toán:
- BMI = weight / (height/100)²
- Nên lưu vào database hay tính động?

#### Cách giải quyết: Tính động khi trả về

```java
// ProfileController.java
private ProfileDto toDto(ProfileEntity entity) {
    ProfileDto dto = new ProfileDto();
    dto.userId = entity.userId;
    dto.age = entity.age;
    dto.height = entity.height;
    dto.weight = entity.weight;
    dto.updatedAt = entity.updatedAt;

    // Tính BMI động khi trả về
    if (entity.height != null && entity.weight != null
            && entity.height > 0) {
        double heightM = entity.height / 100.0;
        dto.bmi = Math.round((entity.weight / (heightM * heightM)) * 10.0) / 10.0;
    } else {
        dto.bmi = null;
    }

    return dto;
}
```

**Lý do:**
1. BMI phụ thuộc vào height và weight → Nếu height/weight thay đổi → BMI cũng thay đổi
2. Lưu BMI vào DB → Phải cập nhật BMI mỗi khi height/weight thay đổi
3. Tính động → Luôn chính xác, không cần cập nhật nhiều nơi

---

### 3.5 Vấn đề 5: Phân trang với MongoDB

#### Bài toán:
Sinh viên chưa quen với Spring Data Pageable phức tạp.

#### Cách giải quyết: Dùng skip + limit đơn giản

```java
@GetMapping
public ResponseEntity<Map<String, Object>> getHistory(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size,
        @RequestParam(required = false) String date,
        @RequestHeader("X-User-Id") String userId) {

    // Điều kiện lọc
    var criteria = Criteria.where("user_id").is(uid);

    // Lọc theo ngày nếu có
    if (date != null && !date.isBlank()) {
        LocalDate localDate = LocalDate.parse(date);
        Instant start = localDate.atStartOfDay(ZoneOffset.UTC).toInstant();
        Instant end = start.plusSeconds(86400); // +1 ngày
        criteria = criteria.and("timestamp").gte(start).lt(end);
    }

    var query = new Query(criteria);

    // Đếm tổng (trước khi phân trang)
    long total = mongoTemplate.count(query, HistoryData.class);

    // Phân trang: skip + limit
    query.with(Sort.by(Direction.DESC, "timestamp"));
    query.skip((long) page * size);
    query.limit(size);

    List<HistoryData> data = mongoTemplate.find(query, HistoryData.class);

    return ResponseEntity.ok(Map.of(
            "page", page,
            "size", size,
            "total", total,
            "data", data
    ));
}
```

**Giải thích:**
- `page = 0, size = 20`: skip 0, limit 20 (trang 1)
- `page = 1, size = 20`: skip 20, limit 20 (trang 2)
- `page = 2, size = 20`: skip 40, limit 20 (trang 3)
- Frontend: `page + 1` để hiển thị số trang 1-based

---

### 3.6 Vấn đề 6: Inner Class vs Separate Entity Files

#### Bài toán:
Nên tách Entity ra file riêng hay định nghĩa trong Controller?

#### Cách giải quyết: Tùy trường hợp

**Dùng Inner Class (gọn, khi Entity chỉ dùng trong 1 Controller):**

```java
// HealthController.java
@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
public class HealthController {
    private final MongoTemplate mongoTemplate;

    // Entity là inner class - chỉ dùng ở đây
    @Document(collection = "realtime_health_data")
    public static class HealthData {
        public String id;
        @Field("user_id") public String userId;
        public Instant timestamp;
        public Double bpm;
        public Double spo2;
        // ... các trường khác
    }

    @GetMapping("/latest")
    public HealthData getLatest(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {
        String uid = UserUtils.extractUserId(userId);
        Query query = new Query(Criteria.where("user_id").is(uid))
                .with(Sort.by(Sort.Direction.DESC, "timestamp"))
                .limit(1);
        return mongoTemplate.findOne(query, HealthData.class);
    }
}
```

**Dùng Separate File (khi dùng chung nhiều Controller):**

```java
// DiaryNote.java - file riêng
@Document(collection = "diary_notes")
public class DiaryNote {
    @Id private String id;
    @Field("user_id") private String userId;
    // ...
}

// DiaryController.java - sử dụng DiaryNote
public class DiaryController {
    private final MongoTemplate mongoTemplate;

    @GetMapping
    public List<DiaryDto> getAll(...) {
        // Sử dụng DiaryNote
        mongoTemplate.find(query, DiaryNote.class);
    }
}
```

---

### 3.7 Vấn đề 7: Xử lý null khi cập nhật (PUT)

#### Bài toán:
Khi cập nhật profile, nếu user chỉ gửi `{"age": 25}` thì height và weight có bị set thành null không?

#### Cách giải quyết: Chỉ cập nhật trường khác null

```java
@PutMapping
public ResponseEntity<ProfileDto> update(
        @RequestBody ProfileDto dto,
        @RequestHeader("X-User-Id") String userId) {

    ProfileEntity profile = mongoTemplate.findOne(
        new Query(Criteria.where("user_id").is(uid)),
        ProfileEntity.class
    );

    // Chỉ cập nhật các trường KHÁC NULL
    if (dto.age != null) {
        profile.age = dto.age;
    }
    if (dto.height != null) {
        profile.height = dto.height;
    }
    if (dto.weight != null) {
        profile.weight = dto.weight;
    }

    mongoTemplate.save(profile);
    return ResponseEntity.ok(toDto(profile));
}
```

---

### 3.8 Vấn đề 8: CORS - Kết nối Frontend với Backend

#### Bài toán:
Frontend chạy ở port 5173, Backend ở port 8080 → Lỗi CORS.

#### Cách giải quyết: Cấu hình CORS trong DashboardApplication

```java
@SpringBootApplication
public class DashboardApplication {
    public static void main(String[] args) {
        SpringApplication.run(DashboardApplication.class, args);
    }

    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOrigins(
                            "http://localhost:5173",
                            "http://localhost:5174",
                            "http://localhost:3000"
                        )
                        .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                        .allowedHeaders("*");
            }
        };
    }
}
```

---

### 3.9 Vấn đề 9: MongoDB Field Name vs Java Field Name

#### Bài toán:
Trong MongoDB: `user_id`, `body_temp`, `gsr_adc`
Trong Java: `userId`, `bodyTemp`, `gsrAdc`

#### Cách giải quyết: Dùng annotation `@Field`

```java
@Data
@Document(collection = "realtime_health_data")
public static class DashboardData {
    public String id;

    // MongoDB: user_id → Java: userId
    @Field("user_id") public String userId;

    // MongoDB: device_id → Java: deviceId
    @Field("device_id") public String deviceId;

    // MongoDB: body_temp → Java: bodyTemp
    @Field("body_temp") public Double bodyTemp;

    // MongoDB: gsr_adc → Java: gsrAdc
    @Field("gsr_adc") public Double gsrAdc;

    // MongoDB: ext_temp_c → Java: extTempC
    @Field("ext_temp_c") public Double extTempC;

    // MongoDB: ext_humidity_pct → Java: extHumidityPct
    @Field("ext_humidity_pct") public Double extHumidityPct;

    // MongoDB: time_slot → Java: timeSlot
    @Field("time_slot") public String timeSlot;
}
```

**Quy tắc đặt tên:**
- MongoDB: snake_case (`user_id`, `body_temp`)
- Java: camelCase (`userId`, `bodyTemp`)
- Annotation `@Field("...")` ánh xạ giữa 2 convention

---

## 4. BẢNG SO SÁNH: THIẾT KẾ BAN ĐẦU VS THIẾT KẾ ĐƠN GIẢN

| Khía cạnh | Thiết kế ban đầu | Thiết kế đơn giản |
|-----------|-----------------|-------------------|
| Authentication | JWT + Filter | Header `X-User-Id` |
| Password | BCrypt hash | Plain text |
| Service Layer | Tách riêng (8 file) | Gộp vào Controller |
| Config | JwtAuthFilter + JwtTokenProvider + SecurityConfig | Chỉ DashboardApplication |
| Độ phức tạp | Cao | Thấp |
| Phù hợp cho | Production | Học tập |
| Số lượng file Java | ~25+ files | ~15 files |
| Thời gian học | 2-4 tuần | 1-2 tuần |

---

## 5. KẾT LUẬN

### 5.1 Đã đạt được
- ✅ Hoàn thành 8/8 Usecase theo yêu cầu
- ✅ Code đơn giản, dễ hiểu cho sinh viên mới học Java
- ✅ Không sử dụng JWT/BCrypt/SecurityConfig
- ✅ Sử dụng `MongoTemplate` + `Query` + `Criteria` nhất quán
- ✅ Mỗi Controller có inline private methods thay cho Service layer
- ✅ Phân trang đơn giản với skip + limit

### 5.2 Hạn chế (chấp nhận cho mục đích học)
- ⚠️ Không bảo mật (plain text password, không có JWT)
- ⚠️ Không có refresh token
- ⚠️ Không có role-based access control
- ⚠️ Không có rate limiting

### 5.3 Hướng phát triển thêm (sau khi học xong cơ bản)
1. Thêm JWT authentication
2. Thêm BCrypt password hashing
3. Thêm Spring Security với roles (ADMIN, USER)
4. Thêm input validation với @Valid
5. Thêm exception handling với @ControllerAdvice
6. Thêm unit tests với JUnit + Mockito
7. Triển khai Docker compose (MongoDB + Backend + Frontend)

### 5.4 Bài học kinh nghiệm
1. **Đơn giản hóa là chìa khóa**: Khi học một công nghệ mới, bắt đầu với phiên bản đơn giản nhất, sau đó mới nâng cấp.
2. **Học qua ví dụ**: Xem một Controller hoạt động tốt (như DiaryController) rồi copy pattern cho các Controller khác.
3. **MongoDB với Spring**: Dùng `MongoTemplate` + `Query` + `Criteria` là đủ cho hầu hết các use case đơn giản.
4. **Inline Service Pattern**: Với ứng dụng nhỏ, gộp Service vào Controller giúp giảm số lượng file và dễ debug hơn.

---

## 6. THÔNG TIN DỰ ÁN

| Thông tin | Chi tiết |
|-----------|----------|
| Tên dự án | IoMT Health Monitoring System |
| Sinh viên | BTL - Đồ án tốt nghiệp |
| Ngôn ngữ Backend | Java 17 + Spring Boot 3.2.3 |
| Database | MongoDB |
| Frontend | React + Vite |
| IoT Backend | Python + FastAPI |
| ML Model | scikit-learn (Random Forest) |
| Thiết bị | ESP32 + DHT11 + MAX30102 + GSR |

---

*Báo cáo được tạo: Tháng 4/2026*
