# 2. Thiết kế phần cứng và phần mềm nhúng

## 2.1. Các module cảm biến

### 2.1.1. Module cảm biến nhịp tim (MAX30105)

Module cảm biến nhịp tim sử dụng cảm biến quang **MAX30105** của hãng Maxim Integrated, kết hợp thuật toán **PPG (Photoplethysmography)** để đo nhịp tim và **SpO2** (nồng độ oxy trong máu). Cảm biến này đo sự hấp thụ ánh sáng của mô và máu thông qua hai bước sóng: đỏ (Red, 650nm) và hồng ngoại (IR, 950nm).

#### 2.1.1.1. Dữ liệu thô

MAX30105 là cảm biến quang I2C với độ phân giải ADC **18-bit** (giá trị từ 0 đến 262,143). Mỗi mẫu dữ liệu PPG bao gồm hai giá trị: **Red** và **IR**, mỗi giá trị chiếm 3 byte dữ liệu I2C (tổng 6 byte/mẫu). Tốc độ lấy mẫu được cấu hình ở mức **1000 Hz** (1 ms/mẫu).

Dữ liệu thô được lưu trữ trong bộ đệm vòng nội bộ của MAX30105 (FIFO) với sức chứa 32 mẫu. Vi điều khiển đọc dữ liệu qua I2C bus tốc độ **400 kHz** trên chân GPIO 12 (SDA) và GPIO 13 (SCL). Chân GPIO 11 được cấu hình làm chân ngắt (INT, cạnh xuống NEGEDGE) để thông báo khi có dữ liệu mới trong FIFO, sử dụng cơ chế **ISR (Interrupt Service Routine) → Task Notification** để đánh thức task xử lý mà không cần polling liên tục.

Cấu hình phần cứng của module:

| Thông số | Giá trị |
|---|---|
| Địa chỉ I2C | 0x57 |
| Chân SDA | GPIO 12 |
| Chân SCL | GPIO 13 |
| Chân ngắt (INT) | GPIO 11 |
| Tốc độ I2C | 400 kHz |
| Tốc độ lấy mẫu | 1000 Hz |
| Độ phân giải ADC | 18-bit |
| LED brightness | 60/255 |

Mỗi mẫu dữ liệu thô bao gồm:

```c
rawRed[i]  // Giá trị ADC 18-bit, ví dụ: 85000–120000
rawIr[i]   // Giá trị ADC 18-bit, ví dụ: 60000–150000
```

Khi ngón tay người dùng đặt lên cảm biến, tín hiệu IR trung bình **IR_mean > 50000** cho thấy có phản xạ ánh sáng từ mô, hệ thống phát hiện người dùng hiện diện và chuyển sang chế độ đo **MODE_ACTIVE**. Nếu IR_mean giảm xuống dưới ngưỡng, hệ thống quay về **MODE_IDLE**.

#### 2.1.1.2. Dữ liệu sau tính toán

Dữ liệu sau tính toán bao gồm hai giá trị: **BPM (nhịp tim/phút)** và **SpO2 (%)**. Quá trình xử lý từ dữ liệu thô đến kết quả cuối cùng trải qua nhiều bước, được thực hiện trong `sensor_hub_task` (task xử lý cảm biến quang) và hàm `maxim_heart_rate_and_oxygen_saturation()` trong file `spo2_algorithm.c`.

**Bước 1 — Thu thập theo lô (Batch Collection):**
Task thu thập **100 mẫu** mỗi lần (100 ms dữ liệu ở 1000 Hz). Mỗi lô dữ liệu chứa 100 giá trị Red và 100 giá trị IR.

**Bước 2 — Lọc Gaussian (Gaussian Filtering):**
Tính trung bình (mean) và độ lệch chuẩn (stddev) của 100 mẫu trong lô hiện tại. Chỉ giữ lại các mẫu nằm trong khoảng **[mean - std, mean + std]**, tối đa 15 mẫu. Bước này loại bỏ các giá trị nhiễu (motion artifact, spike) một cách thống kê.

**Bước 3 — Cập nhật bộ đệm xoay (Rolling Buffer):**
15 mẫu tốt nhất được thêm vào cuối bộ đệm xoay, 85 mẫu đầu tiên được dịch sang trái. Bộ đệm xoay giữ **100 mẫu liên tục** (1 giây dữ liệu), được sử dụng làm đầu vào cho thuật toán tính BPM/SpO2.

**Bước 4 — Xử lý tín hiệu số (Digital Signal Processing):**
Hàm `maxim_heart_rate_and_oxygen_saturation()` thực hiện chuỗi bộ lọc:

```
1. Bộ lọc trung vị 3 điểm (3-point Median Filter)
   → Loại bỏ spike ngẫu nhiên

2. Bộ lọc thông cao Butterworth bậc 2 (0.5 Hz @ 100 Hz)
   → Loại bỏ drift baseline (thành phần DC)
   Hệ số: b = [0.97803, -1.95607, 0.97803]
           a = [1, -1.95558, 0.95654]

3. Bộ lọc thông thấp Butterworth bậc 2 (4 Hz @ 100 Hz)
   → Loại bỏ nhiễu tần số cao
   Hệ số: b = [0.01336, 0.02672, 0.01336]
           a = [1, -1.64746, 0.70090]

4. Phát hiện đỉnh (Peak Detection)
   → Ngưỡng = max(signal) / 2, giới hạn [30, 60]
   → Khoảng cách tối thiểu giữa 2 đỉnh: 33 mẫu (330 ms)
     để tránh phát hiện sai ở tần số harmonics
   → Kiểm tra tính nhất quán: các khoảng cách đỉnh phải
     có độ lệch < 10 mẫu (100 ms), nếu không → không hợp lệ
```

**Công thức tính BPM:**

```
BPM = 6000 / avg_peak_interval
Trong đó avg_peak_interval = trung bình cộng các khoảng cách đỉnh (tính bằng số mẫu)
```

Ví dụ: nếu trung bình có 72 đỉnh/phút → interval = 100000/72 ≈ 833 ms → BPM = 6000/833 ≈ 72

**Công thức tính SpO2 (R-ratio):**

```
DC_red  = mean(rawRed[i])                          // Thành phần một chiều
DC_ir   = mean(rawIr[i])                           // Thành phần một chiều
AC_red  = sqrt(sum((rawRed[i] - DC_red)^2) / n)  // RMS biến đổi đỏ
AC_ir   = sqrt(sum((rawIr[i] - DC_ir)^2) / n)    // RMS biến đổi hồng ngoại

R = (AC_red / DC_red) / (AC_ir / DC_ir)           // Tỷ số R

SpO2 = -45.60 × R² + 30.354 × R + 94.845           // Công thức thực nghiệm Maxim
```

Kết quả SpO2 được giới hạn trong khoảng **[70%, 100%]**.

**Bước 5 — Bộ đệm kết quả và lọc cuối cùng:**
Kết quả BPM/SpO2 tức thời từ thuật toán được lưu vào bộ đệm kết quả 10 giây (200 mẫu). Sau mỗi **10 giây**, hệ thống tính trung bình và độ lệch chuẩn của bộ đệm, chỉ giữ lại các giá trị nằm trong khoảng **[mean - std, mean + std]** để loại bỏ outlier cuối cùng, sau đó tính trung bình làm **kết quả xuất ra**.

**Lưu đồ dòng dữ liệu tổng hợp:**

```
MAX30105 FIFO (18-bit, 1000 Hz)
    │
    ▼
ISR (GPIO 11 NEGEDGE) → ulTaskNotifyGive
    │
    ▼
sensor_hub_task: 100 mẫu/lô
    │
    ├── Gaussian Filter (mean ± stddev)
    │       ↓
    │   Tối đa 15 mẫu "tốt"
    │       ↓
    │   Cập nhật Rolling Buffer (100 mẫu)
    │       ↓
    │   maxim_heart_rate_and_oxygen_saturation()
    │       ├── 3-point Median
    │       ├── Butterworth HPF (0.5 Hz)
    │       ├── Butterworth LPF (4 Hz)
    │       ├── Peak Detection + Consistency Check
    │       │       ↓ BPM tức thời
    │       └── R-ratio + Maxim formula
    │               ↓ SpO2 tức thời
    │       ↓ (lưu vào bộ đệm 200 mẫu)
    │
    ▼ Mỗi 10 giây
Lọc outlier (mean ± stddev)
    │
    ▼
data->bpm, data->spo2 (xuất ra cuối cùng)
```

**Các thông số cấu hình quan trọng:**

| Thông số | Giá trị |
|---|---|
| Lô dữ liệu mỗi lần xử lý | 100 mẫu (100 ms) |
| Bộ đệm xoay xử lý | 100 mẫu |
| Bộ đệm kết quả 10 giây | 200 mẫu |
| Chu kỳ cập nhật kết quả cuối | 10 giây |
| Ngưỡng phát hiện người dùng (IR mean) | > 50000 |
| Tần số cắt bộ lọc thông cao | 0.5 Hz |
| Tần số cắt bộ lọc thông thấp | 4 Hz |
| Khoảng trễ tối thiểu giữa 2 đỉnh | 330 ms |
| Ngưỡng nhất quán khoảng cách đỉnh | ±10 mẫu (±100 ms) |
| Bỏ qua mẫu khởi động | 6 lần đo đầu (chống artifact) |

---

### 2.1.2. Module cảm biến nhiệt độ cơ thể (DS18B20)

Module cảm biến nhiệt độ cơ thể sử dụng **DS18B20** — cảm biến nhiệt độ kỹ thuật số giao thức 1-Wire của hãng Maxim Integrated. DS18B20 được chọn vì độ chính xác cao (±0.5°C), khả năng đọc không đồng bộ qua RMT hardware, và không cần chuyển đổi ADC. Dữ liệu nhiệt độ từ DS18B20 được xử lý qua **thermal_processor** — một pipeline 5 tầng phức tạp — để tính ra nhiệt độ lõi cơ thể (core body temperature).

#### 2.1.2.1. Dữ liệu thô

DS18B20 giao tiếp qua giao thức **1-Wire** trên chân GPIO 3, sử dụng driver **RMT (Remote Control Transceiver)** của ESP-IDF để tạo xung timing chính xác ở mức micro giây mà không blocking CPU. Cảm biến hoạt động ở độ phân giải **12-bit**, cho phép đọc nhiệt độ với độ phân giải 0.0625°C.

Dữ liệu thô trả về từ DS18B20 là giá trị nhiệt độ dưới dạng **số thực (float)**, ví dụ: `32.5°C`, `28.3°C`, `25.0°C`. Khi chưa có người dùng (MODE_IDLE), DS18B20 đo nhiệt độ phòng. Khi có người dùng (MODE_ACTIVE), DS18B20 đo nhiệt độ bề mặt da ngón tay (skin temperature).

Task `ds18b20_task` gọi `ds18b20_sensor_get_temp()` mỗi **1 giây** để lấy nhiệt độ thô, sau đó truyền giá trị này vào thermal_processor cùng với trạng thái người dùng (`is_user_present`), nhiệt độ môi trường từ DHT11, và độ ẩm từ DHT11.

| Thông số | Giá trị |
|---|---|
| Chân Data | GPIO 3 |
| Giao thức | 1-Wire (RMT hardware) |
| Độ phân giải | 12-bit (0.0625°C) |
| Chu kỳ đọc | 1 giây |
| Khoảng nhiệt độ hợp lệ (thô) | -55°C đến +125°C |

#### 2.1.2.2. Dữ liệu sau tính toán

Dữ liệu sau tính toán là **nhiệt độ cơ thể bù (compensated body temperature)** — ước tính nhiệt độ lõi từ nhiệt độ bề mặt da. Nhiệt độ bề mặt da luôn thấp hơn nhiệt độ lõi do gradient nhiệt từ trong ra ngoài cơ thể. Hệ thống sử dụng mô hình truyền nhiệt để bù độ trễ và ước tính giá trị cân bằng cuối cùng.

Pipeline xử lý nhiệt độ (thermal_processor) bao gồm **6 tầng chính**:

```
DS18B20 raw_temp
    │
    ▼
Tầng 0: WARM START
    Khi phát hiện người chạm tay:
    → Kalman.x = T_ambient + 7.0°C (prior sinh lý)
    → Kalman.P = 16.0 (uncertainty cao → tin measurement)
    │
    ▼
Tầng 1: BỘ LỌC TRUNG VỊ (Median Filter, cửa sổ 5 mẫu)
    → Loại bỏ spike nhiễu (điện trở tiếp xúc kém, nhiễu điện từ)
    │
    ▼
Tầng 2: BỘ LỌC KALMAN 1D
    Q = 0.05 (nhiễu quá trình), R = 1.0 (nhiễu đo lường)
    → Ước lượng trạng thái tối ưu theo phương pháp Bayesian
    │
    ▼
Tầng 3: BỘ LỌC EMA THÍCH ỨNG (Adaptive EMA)
    α = 0.40 khi |dT| > 0.5°C  (thay đổi nhanh → bắt tín hiệu)
    α = 0.20 khi |dT| > 0.2°C  (trung bình)
    α = 0.08 khi |dT| ≤ 0.2°C  (ổn định → lọc mạnh)
    │
    ▼
Tầng 4a: SENSOR FUSION — Chỉnh bias DHT11
    Học dần độ lệch giữa DS18B20 và DHT11 khi IDLE
    bias_correction += 0.005 × (T_DS18B20 - T_DHT11)
    │
    ▼
Tầng 4b: MÔ HÌNH BÙ NHIỆT ĐỘNG (Dual-Sensor Compensation)
    T_core = T_skin + k × (T_skin - T_ambient)
    
    Trong đó k = 0.40 × humidity_factor × vaso_factor
    
    - humidity_factor = 1.0 - (humidity - 50) × 0.003
      (clamp [0.85, 1.15])
    - vaso_factor = 1.0 + (22 - T_ambient) × 0.008
      khi T_ambient < 22°C (co mạch ngoại vi)
      (clamp tối đa 1.25)
    │
    ▼
Tầng 4c: CỔNG SINH LÝ (Physiological Gate)
    Loại bỏ: T_skin < 28°C hoặc T_skin > 40°C
    Loại bỏ: |dT/dt| > 0.15°C/s (chưa cân bằng)
    │
    ▼
Tầng 5: DỰ BÁO ASYMPTOTIC (Three-Point Extrapolation)
    Mỗi 4 giây, lấy 3 điểm: đầu, giữa, cuối buffer 12 mẫu
    Ngoại suy T_inf = (T1×T3 - T2²) / (T1 + T3 - 2×T2)
    → Xác nhận ổn định khi 3 lần predict liên tiếp
      có spread < 0.25°C
    → Kết quả: T_final = 0.6 × T_inf_stable + 0.4 × T_skin_current
    │
    ▼
Tầng 6: CỔNG ỔN ĐỊNH (Stability Gate)
    Chấp nhận kết quả khi: |T - last_stable| < 0.1°C
    liên tục trong 5 chu kỳ
    │
    ▼
data->body_temp (nhiệt độ cơ thể cuối cùng)
data->confidence (0–100)
```

**Mô hình toán học cốt lõi:**

Hệ thống áp dụng **định luật Newton về làm mát** để mô hình hóa truyền nhiệt từ lõi cơ thể ra bề mặt da. Nhiệt độ lõi ước tính:

```
T_core = T_skin + k × (T_skin − T_ambient)
```

Với hệ số k động, phụ thuộc:

- **Độ ẩm** (humidity): Khi độ ẩm cao, mồ hôi bay hơi kém hơn → khả năng tản nhiệt giảm → k tăng
- **Co mạch ngoại vi** (vasoconstriction): Khi trời lạnh (< 22°C), mạch máu ngoại vi co lại → khoảng cách T_skin–T_core tăng → k tăng

**Hệ số k = THERMAL_K_BASE × humidity_factor × vaso_factor:**

| Tình trạng | k |
|---|---|
| Trung bình (humidity=50%, T_amb=25°C) | 0.40 |
| Độ ẩm cao (humidity=80%) | ~0.36 |
| Độ ẩm thấp (humidity=20%) | ~0.44 |
| Lạnh (T_amb=15°C) | ~0.45 |
| Rất lạnh (T_amb=10°C) | ~0.50 |

**Confidence score (0-100):**

| Giá trị | Ý nghĩa |
|---|---|
| 0 | Dữ liệu không hợp lệ hoặc lỗi cảm biến |
| 50 | Đang thu thập dữ liệu, chưa đủ điểm predict |
| 75 | Đã có đủ điểm predict nhưng chưa ổn định |
| 100 | T_inf đã ổn định, kết quả đáng tin cậy |

---

### 2.1.3. Module cảm biến nhiệt độ và độ ẩm môi trường (DHT11)

Module cảm biến môi trường sử dụng **DHT11** — cảm biến nhiệt độ và độ ẩm kỹ thuật số giá rẻ của Aosong Electronics. DHT11 cung cấp dữ liệu nhiệt độ phòng và độ ẩm tương đối, phục vụ hai mục đích: (1) làm đầu vào cho mô hình bù nhiệt của DS18B20, và (2) hiển thị thông số môi trường trên OLED.

#### 2.1.3.1. Dữ liệu thô

DHT11 giao tiếp qua **giao thức single-wire** (1 dây dữ liệu + 1 dây nguồn + 1 dây ground), chân GPIO 4. Giao thức yêu cầu timing chính xác ở mức micro giây, do đó phần đọc dữ liệu được thực hiện trong **critical section** (`portENTER_CRITICAL / portEXIT_CRITICAL`) để tránh bị ngắt làm sai timing.

DHT11 trả về **40 bit dữ liệu** (= 5 byte) trong mỗi lần đọc:

| Byte | Nội dung | Ví dụ |
|---|---|---|
| Byte 0 | Humidity integer (phần nguyên độ ẩm) | 65 |
| Byte 1 | Humidity decimal (DHT11 luôn = 0) | 0 |
| Byte 2 | Temperature integer (phần nguyên nhiệt độ) | 25 |
| Byte 3 | Temperature decimal (DHT11 luôn = 0) | 0 |
| Byte 4 | Checksum = (Byte0+Byte1+Byte2+Byte3) & 0xFF | 90 |

Quy trình đọc dữ liệu:

```
1. Host kéo chân DATA xuống LOW trong 18–20 ms (start signal)
2. DHT11 kéo DATA LOW trong 80 µs rồi HIGH trong 80 µs (response)
3. Host bắt đầu nhận 40 bit:
   - Mỗi bit bắt đầu bằng xung LOW 50 µs
   - Tiếp theo là xung HIGH:
     → Nếu HIGH > 40 µs → bit = 1
     → Nếu HIGH ≤ 40 µs → bit = 0
4. Checksum được kiểm tra (Byte0+Byte1+Byte2+Byte3 = Byte4)
```

Thời gian chờ tối thiểu giữa hai lần đọc liên tiếp: **2 giây** (theo datasheet DHT11). Nếu đọc thất bại liên tiếp 5 lần, hệ thống tự reset cảm biến.

| Thông số | Giá trị |
|---|---|
| Chân Data | GPIO 4 |
| Độ phân giải nhiệt độ | 1°C (8-bit) |
| Độ phân giải độ ẩm | 1% (8-bit) |
| Khoảng nhiệt độ hoạt động | 0–50°C |
| Khoảng độ ẩm hoạt động | 20–90% RH |
| Chu kỳ polling | 2 giây |
| Số bit dữ liệu | 40 bit (5 byte) |
| Reset sau lỗi liên tiếp | 5 lần |

#### 2.1.3.2. Dữ liệu sau tính toán

Dữ liệu sau tính toán từ DHT11 được lưu vào ba biến trong `health_data_t`:

- `data->humidity` — độ ẩm tương đối (0–100%), không qua xử lý (đã được checksum verify)
- `data->dht11_temperature` — nhiệt độ thô từ DHT11 (ví dụ: 25.0°C), chủ yếu dùng để debug
- `data->ambient_temp` — nhiệt độ môi trường qua **EMA filter** với hệ số α = 0.2

**Công thức EMA cho ambient_temp:**

```
ambient_temp = 0.2 × T_DHT11 + 0.8 × ambient_temp_previous
```

EMA filter giúp loại bỏ các spike nhiệt độ đột ngột do nhiễu hoặc gió thổi trực tiếp vào cảm biến, đồng thời vẫn phản ánh xu hướng thay đổi nhiệt độ phòng theo thời gian. Giá trị `ambient_temp` được truyền vào thermal_processor để tính hệ số k động cho mô hình bù nhiệt của DS18B20.

**Độ chính xác và hạn chế của DHT11:**

DHT11 có sai số ±2°C và ±5% RH theo datasheet, do đó hệ thống áp dụng cơ chế **bias correction tự học** trong thermal_processor: khi ở trạng thái IDLE (không có người dùng), DS18B20 đo nhiệt độ phòng gần như chính xác (±0.5°C), hệ thống so sánh với DHT11 và học dần độ lệch `dht11_bias_correction` với tốc độ rất chậm (α = 0.005). Khi độ lệch giữa hai cảm biến vượt quá 3°C, hệ thống cảnh báo có thể cảm biến bị lỗi.

---

### 2.1.4. Module cảm biến Stress (GSR)

Module cảm biến stress sử dụng **GSR (Galvanic Skin Response)** — đo sự thay đổi điện trở da (galvanic skin response) để đánh giá mức độ căng thẳng (stress) của người dùng. Nguyên lý hoạt động dựa trên thực tế sinh lý: khi một người căng thẳng, tuyến mồ hôi hoạt động mạnh hơn, làm giảm điện trở da. Đây là phương pháp đo phổ biến trong lĩnh vực **biofeedback** và **psychophysiology**.

#### Nguyên lý hoạt động

Mạch đo GSR trong hệ thống sử dụng phương pháp **đo điện áp qua điện trở da**. Người dùng chạm hai ngón tay vào hai điểm tiếp xúc điện cực trên thiết bị. ESP32 đọc giá trị điện áp qua chân ADC và chuyển đổi sang giá trị GSR.

#### 2.1.4.1. Dữ liệu thô

Dữ liệu GSR thô được đo bằng **ADC 12-bit** của ESP32 trên kênh **ADC1_CH3** (GPIO 4). Mỗi lần đọc, hệ thống thực hiện **20 phép đo** và tính trung bình để giảm nhiễu:

```c
sum = 0;
for (i = 0; i < 20; i++) {
    adc_oneshot_read(ADC_UNIT_1, ADC_CHANNEL_3, &analog_val);
    sum += analog_val;
}
gsr_raw = sum / 20;  // Trung bình 20 mẫu
```

Kết quả thô là giá trị ADC 12-bit, phạm vi **0–4095**. Điện trở da người khỏe mạnh ở trạng thái nghỉ thường nằm trong khoảng **50–500 kΩ**, tương ứng với giá trị ADC khoảng **1500–2500** (tùy mạch phân áp).

| Thông số | Giá trị |
|---|---|
| Chân đo | GPIO 4 (ADC1_CH3) |
| Đơn vị ADC | ADC_UNIT_1 |
| Kênh ADC | ADC_CHANNEL_3 |
| Độ phân giải ADC | 12-bit (0–4095) |
| Số mẫu mỗi lần đọc | 20 |
| Chu kỳ đọc | ~50 ms |
| Baseline mặc định | 2200 |

#### 2.1.4.2. Dữ liệu sau tính toán

Giá trị GSR cuối cùng được tính bằng công thức:

```
GSR = GSR_raw + GSR_offset
```

Trong đó `GSR_offset = GSR_TARGET_BASELINE − GSR_raw_user`, với `GSR_TARGET_BASELINE = 2200`.

**Cơ chế hiệu chuẩn (Calibration):**

Mỗi người dùng có mức điện trở da khác nhau do đặc điểm sinh lý cá nhân (độ dày da, độ ẩm da, điểm tiếp xúc điện cực). Hệ thống sử dụng cơ chế hiệu chuẩn cá nhân hóa:

1. **Chế độ CALIBRATE**: Người dùng ở trạng thái IDLE (không đo nhịp tim), nhấn giữ nút **BOOT (GPIO 0)** trong **3 giây** để vào chế độ CALIBRATE
2. Hệ thống đọc `GSR_raw` thực tế của người dùng
3. Nhấn giữ BOOT thêm 3 giây để xác nhận và lưu offset vào **NVS (Non-Volatile Storage)**
4. Offset được tính: `GSR_offset = 2200 − GSR_raw_user`
5. Giá trị GSR sau hiệu chuẩn: `GSR = GSR_raw + GSR_offset = 2200`

Ví dụ:
- Người dùng A có GSR_raw = 1800 → offset = 400 → GSR = 2200
- Người dùng B có GSR_raw = 2500 → offset = -300 → GSR = 2200

Cả hai người dùng sau hiệu chuẩn đều có GSR = 2200 (baseline), bất kể điện trở da cá nhân khác nhau. Điều này cho phép so sánh **mức thay đổi stress** giữa các lần đo trên cùng một người dùng:

- **GSR > 2200**: Stress tăng so với baseline (mồ hôi nhiều hơn, điện trở da giảm)
- **GSR < 2200**: Stress giảm so với baseline (thư giãn)
- **GSR = 2200**: Baseline (trạng thái bình thường của người dùng đó)

**Lưu trữ bền vững (NVS):**

Thông tin hiệu chuẩn GSR được lưu vào NVS namespace `"gsr_cal"` với các key:

| Key | Nội dung |
|---|---|
| `gsr_offset` | Giá trị offset hiệu chuẩn |
| `gsr_baseline` | Baseline mục tiêu (2200) |
| `calibrate_done` | Cờ hiệu chuẩn hoàn tất |

Khi thiết bị khởi động lại, offset được đọc từ NVS và áp dụng tự động mà không cần hiệu chuẩn lại.

**Trạng thái hệ thống và GSR:**

| System Mode | Hành vi GSR |
|---|---|
| MODE_CONFIG | Không đo GSR |
| MODE_IDLE | Đo GSR raw, hiển thị, không publish MQTT |
| MODE_ACTIVE | Đo GSR, publish MQTT mỗi 1 giây |
| MODE_CALIBRATE | Hiển thị GSR raw, chờ hiệu chuẩn |

---

## 2.2. Vi xử lý trung tâm

### 2.2.1. ESP32 (chip ESP32-WROOM-32D)

Vi xử lý trung tâm của hệ thống là **ESP32** (không phải ESP32-S3 theo cấu hình sdkconfig, mặc dù module phần cứng vật lý là ESP32-S3 Super Mini với 4 MB flash). ESP32 là system-on-chip của Espressif với tích hợp Wi-Fi và Bluetooth, được sử dụng rộng rãi trong các ứng dụng IoT nhờ giá thành thấp, tiêu thụ năng lượng hiệu quả, và hệ sinh thái phần mềm phong phú (ESP-IDF).

#### Thông số kỹ thuật phần cứng

| Thông số | Giá trị |
|---|---|
| Kiến trúc CPU | Xtensa LX6, 32-bit |
| Số lõi | 2 |
| Tần số CPU | 160 MHz |
| SRAM | ~520 KB |
| Flash | 2 MB (SPI, DIO mode, 40 MHz) |
| Wi-Fi | 802.11 b/g/n (2.4 GHz) |
| Bluetooth | Không kích hoạt (CONFIG_BT_ENABLED=n) |
| GPIO | 40 chân (GPIO 0–39) |
| ADC | 2 đơn vị, 10 kênh, 12-bit (0–4095) |
| I2C | 2 bus (I2C_NUM_0, I2C_NUM_1) |
| UART | 3 cổng |
| RMT | Có (dùng cho DS18B20 1-Wire) |
| ESP-IDF version | 6.0.0 |

#### Cấu hình bộ nhớ và Partition Table

Hệ thống sử dụng custom partition table với 4 phân vùng:

```
Offset    Size     Name       Type    SubType
0x8000    —        —          Bootloader
0x9000    24 KB    nvs        data    nvs       (WiFi credentials, GSR calibration)
0xF000    4 KB     phy_init   data    phy       (RF calibration data)
0x10000   3 MB     factory    app     factory   (Main application)
0x310000  64 KB   coredump   data    coredump  (Core dump on crash)
```

Phân vùng `nvs` 24 KB lưu trữ: credentials WiFi (SSID/password), GSR calibration offset, và các thông số cấu hình khác. Phân vùng `factory` 3 MB chứa firmware chính, đủ lớn cho tất cả các component (MAX30105, DS18B20, DHT11, GSR, MQTT, SSD1306 OLED, WiFi manager).

#### Sơ đồ chân GPIO

| GPIO | Chức năng | Giao thức | Component |
|---|---|---|---|
| 0 | BOOT / Calibrate button | GPIO Input | gsr_sensor |
| 3 | DS18B20 Data | 1-Wire (RMT) | app_ds18b20 |
| 4 | DHT11 Data / GSR ADC | Single-wire + ADC | dht11_sensor, gsr_sensor |
| 6 | SSD1306 SDA | I2C Bus 0 | ssd1306 |
| 7 | SSD1306 SCL | I2C Bus 0 | ssd1306 |
| 11 | MAX30105 INT | GPIO Interrupt | sensor_hub |
| 12 | MAX30105 SDA | I2C Bus 1 | max30105 |
| 13 | MAX30105 SCL | I2C Bus 1 | max30105 |

**Lưu ý thiết kế:** GPIO 4 dùng chung cho DHT11 (single-wire output) và GSR (ADC input). Hai chức năng này không hoạt động đồng thời — khi đo GSR, hệ thống không đọc DHT11 và ngược lại. Đây là trade-off hợp lý vì cả hai cảm biến này không yêu cầu đọc real-time.

#### Cấu hình I2C

Hệ thống sử dụng **2 bus I2C tách biệt**, mỗi bus có mutex riêng để tránh xung đột:

| Bus | Thiết bị | SDA | SCL | Tốc độ | Mutex |
|---|---|---|---|---|---|
| I2C_NUM_0 | SSD1306 OLED (0x3C) | GPIO 6 | GPIO 7 | 400 kHz | `i2c_mutex_oled` |
| I2C_NUM_1 | MAX30105 (0x57) | GPIO 12 | GPIO 13 | 400 kHz | `i2c_mutex_max` |

Việc tách bus I2C giúp SSD1306 (OLED 128×64) và MAX30105 hoạt động độc lập mà không ảnh hưởng lẫn nhau. Mutex đảm bảo truy cập đồng thời an toàn khi có ISR hoặc task switching.

#### Khởi động hệ thống

Quy trình khởi động trong `app_main()`:

```
1. nvs_flash_init()          — Khởi tạo NVS (flash layer)
2. health_data_init()        — Tạo EventGroup, khởi tạo health_data_t
3. wifi_manager_init()       — WiFi Provisioning (SoftAP + STA)
4. sntp_init_time()          — Đồng bộ NTP (pool.ntp.org, UTC+7)
5. sensor_hub_i2c_init()    — Khởi tạo 2 bus I2C + mutex
6. Tạo 6 FreeRTOS task
```

#### Bảo mật và Watchdog

- **Brownout detector**: Bật, mức 0 (thấp nhất), tự reset khi VDD < 2.43V
- **Task WDT**: Bật, timeout 5 giây cho tất cả task
- **Interrupt WDT**: Bật, timeout 300 ms
- **Bootloader WDT**: Bật, timeout 9 giây
- **Flash encryption**: Tắt
- **Secure boot**: Tắt

---

### 2.2.2. Hệ điều hành FreeRTOS

Hệ thống sử dụng **FreeRTOS** — hệ điều hành thời gian thực (RTOS) chạy trên ESP-IDF — để quản lý đa tác vụ, đồng bộ hóa, và lập lịch CPU. ESP32 với 2 lõi CPU cho phép các task chạy song song thực sự.

#### Kiến trúc đa tác vụ

Hệ thống bao gồm **6 task ứng dụng** và các task hệ thống:

| Task | Priority | Stack | Core | Chức năng |
|---|---|---|---|---|
| sensor_hub | **5 (cao nhất)** | 8192 | Any | Xử lý PPG MAX30105 → BPM/SpO2 |
| monitor_task | **4** | 8192 | Any | MQTT publish + Serial log |
| ds18b20_task | **3** | 4096 | Any | DS18B20 + thermal processor |
| gsr_sensor | **3** | 4096 | Any | GSR ADC + calibration button |
| dht11_task | **3** | 4096 | Any | DHT11 humidity/temperature |
| display_task | **3** | 4096 | Any | SSD1306 OLED UI |
| wifi_manager | Event-driven | — | — | SoftAP + STA provisioning |
| ESP-MQTT task | ESP-MQTT | 8192 | — | MQTT client (built-in) |
| ipc0 / ipc1 | System | 1024 | CPU0/CPU1 | Inter-processor call |
| esp_timer | System | 3584 | CPU0 | High-resolution timer |
| Tmr Svc | System (prio 1) | 2048 | Any | FreeRTOS timer service |
| IDLE | System (prio 0) | 1536 | Both | Idle task (WDT feed) |

**Priority 0** là thấp nhất, **Priority 5** là cao nhất trong ứng dụng. Tất cả task ứng dụng chạy ở priority 3–5, đảm bảo không bị chiếm bởi các tác vụ hệ thống.

#### Cơ chế đồng bộ hóa

Hệ thống sử dụng ba cơ chế đồng bộ chính:

**1. EventGroup (Event Group):**

```c
#define WIFI_CONNECTED_BIT BIT0  // = 0x01

// wifi_manager: đặt bit khi WiFi kết nối thành công
xEventGroupSetBits(health_data_get_event_group(), WIFI_CONNECTED_BIT);

// wifi_manager: xóa bit khi mất kết nối
xEventGroupClearBits(health_data_get_event_group(), WIFI_CONNECTED_BIT);

// Tất cả sensor task: chờ bit trước khi hoạt động
xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
```

Tất cả 6 sensor/display task đều chờ `WIFI_CONNECTED_BIT` trước khi bắt đầu vòng lặp chính. Điều này đảm bảo:
- Không có task nào gửi dữ liệu lên MQTT khi chưa có WiFi
- Không có task nào spam log khi chưa kết nối mạng
- Tiết kiệm pin (không đo liên tục khi không có nhu cầu)

**2. SemaphoreHandle_t (Mutex — I2C Bus Protection):**

```c
// sensor_hub.c
SemaphoreHandle_t i2c_mutex_oled = xSemaphoreCreateMutex();
SemaphoreHandle_t i2c_mutex_max = xSemaphoreCreateMutex();

// Khi đọc MAX30105:
xSemaphoreTake(i2c_mutex_max, portMAX_DELAY);
max30105_check(&sensor);
xSemaphoreGive(i2c_mutex_max);
```

Hai mutex riêng biệt cho hai bus I2C đảm bảo:
- OLED và MAX30105 truy cập bus độc lập, không chờ nhau
- Interrupt (ISR) và Task truy cập I2C an toàn (ISR chỉ dùng `FromISR` variant)

**3. Task Notification (ISR → Task):**

```c
// ISR (GPIO 11 NEGEDGE — MAX30105 INT)
static void IRAM_ATTR max30105_isr_handler(void *arg) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    vTaskNotifyGiveFromISR(s_sensor_task_handle, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) portYIELD_FROM_ISR();
}

// sensor_hub_task: chờ thông báo thay vì polling
while (1) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);  // Block vô hạn
    // Đọc FIFO, xử lý dữ liệu
}
```

ISR trên GPIO 11 phát hành task notification đến `sensor_hub_task` mỗi khi MAX30105 có dữ liệu mới trong FIFO. Điều này hiệu quả hơn polling vì CPU không bị busy-wait trong khi chờ dữ liệu.

#### Shared Data Module (Singleton Pattern)

Dữ liệu từ tất cả cảm biến được tập trung trong một struct duy nhất `health_data_t`, truy cập qua con trỏ singleton:

```c
// health_data.c
static health_data_t s_health_data = { 0 };

health_data_t *health_data_get(void) {
    return &s_health_data;
}

// Mọi task đều truy cập qua con trỏ này:
health_data_t *data = health_data_get();
data->bpm = 72;
data->body_temp = 36.8f;
```

| Trường dữ liệu | Kiểu | Nguồn |
|---|---|---|
| `bpm` | int | sensor_hub_task |
| `spo2` | int | sensor_hub_task |
| `gsr` | int | gsr_sensor_task |
| `body_temp` | float | ds18b20_task + thermal_processor |
| `room_temp` | float | ds18b20_task + thermal_processor |
| `humidity` | int | dht11_task |
| `ambient_temp` | float | dht11_task (EMA filtered) |
| `gsr_raw` | int32_t | gsr_sensor_task |
| `gsr_offset` | int32_t | gsr_sensor_task (calibration) |
| `gsr_baseline` | int32_t | gsr_sensor_task (= 2200) |
| `is_user_present` | bool | sensor_hub_task |
| `mode` | system_mode_t | Tất cả task |
| `calibrate_done` | bool | gsr_sensor_task |
| `measurement_confidence` | uint8_t | thermal_processor |
| `mac_address` | char[18] | wifi_manager |

#### MQTT Integration

Module MQTT (`mqtt_manager.c`) sử dụng ESP-MQTT built-in của ESP-IDF với cấu hình TLS/SSL:

| Thông số | Giá trị |
|---|---|
| Broker | HiveMQ Cloud |
| Endpoint | `mqtts://6b09ec30252741efa972f3f845ce726d.s1.eu.hivemq.cloud:8883` |
| Username | Ptit1234 |
| Password | Ptit1234 |
| Topic | `ptit/health/data` |
| QoS | 0 (fire-and-forget) |
| Transport | MQTTS (TLS/SSL) |

MQTT publish chỉ thực hiện khi `mode != MODE_IDLE`:

| Mode | MQTT interval | Serial log interval |
|---|---|---|
| MODE_CONFIG | Không publish | Không log |
| MODE_IDLE | Không publish | 60 giây |
| MODE_ACTIVE | 1 giây | 100 ms |
| MODE_CALIBRATE | 60 giây | 100 ms |

JSON payload gửi lên MQTT:

```json
{
  "timestamp": "2026-04-15 - 10:30:45",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "mode": 2,
  "dht11_room_temp": 27.5,
  "dht11_humidity": 65,
  "body_temp": 36.8,
  "bpm": 72,
  "spo2": 97,
  "gsr": 2200,
  "confidence": 100,
  "dht11_bias": 0.125
}
```

#### WiFi Manager (Provisioning)

WiFi manager sử dụng **ESP Wi-Fi Provisioning** (component `wifi_provisioning` của ESP-IDF) với cơ chế SoftAP + HTTP server:

1. **Lần đầu khởi động** (chưa có credentials trong NVS):
   - ESP32 khởi động **SoftAP** với SSID `"IoMT-PTIT"` (không có mật khẩu)
   - HTTP server cung cấp giao diện web để người dùng nhập SSID/password WiFi
   - Sau khi nhận credentials, kết nối STA

2. **Khởi động lại** (đã có credentials trong NVS):
   - Đọc credentials từ NVS
   - Kết nối trực tiếp STA (bỏ qua SoftAP)
   - Retry 5 lần nếu thất bại, sau đó reset và quay lại SoftAP

3. **SNTP**: Đồng bộ thời gian qua `pool.ntp.org`, múi giờ **ICT (UTC+7)**, dùng cho timestamp trong MQTT payload

#### Sơ đồ kiến trúc phần mềm tổng hợp

```
┌─────────────────────────────────────────────────────────┐
│                      app_main()                          │
│  NVS init → health_data_init → wifi_manager_init →     │
│  sntp_init → sensor_hub_i2c_init → Tạo 6 Task           │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴─────────────────────────────────────┐
    │           FreeRTOS Scheduler                      │
    │                                                   │
    │  ┌─ Priority 5 ─────────────────────────────────┐│
    │  │ sensor_hub_task                              ││
    │  │ ISR (GPIO11) → TaskNotify                    ││
    │  │ MAX30105 I2C (mutex_max) → BPM/SpO2          ││
    │  └──────────────────────────────────────────────┘│
    │                                                   │
    │  ┌─ Priority 4 ─────────────────────────────────┐│
    │  │ monitor_task                                ││
    │  │ WiFi Event → MQTT publish (1s/60s)          ││
    │  │ Serial log (100ms/60s)                       ││
    │  └──────────────────────────────────────────────┘│
    │                                                   │
    │  ┌─ Priority 3 ─────────────────────────────────┐│
    │  │ ds18b20_task     ds18b20 + thermal_processor ││
    │  │ gsr_sensor_task  ADC12 + NVS calibration     ││
    │  │ dht11_task       Single-wire + EMA filter    ││
    │  │ display_task     SSD1306 OLED (mutex_oled)   ││
    │  └──────────────────────────────────────────────┘│
    │                                                   │
    │  ┌─ System ─────────────────────────────────────┐│
    │  │ wifi_manager   SoftAP + STA provisioning      ││
    │  │ ESP-MQTT task  TLS/SSL MQTT client           ││
    │  │ esp_timer      High-res timer service         ││
    │  └──────────────────────────────────────────────┘│
    └───────────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │           health_data_t (Singleton)              │
    │  bpm, spo2, gsr, body_temp, room_temp,          │
    │  humidity, ambient_temp, is_user_present,       │
    │  mode, measurement_confidence, gsr_offset...    │
    └────────────────┬────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │  EventGroup         │
          │  WIFI_CONNECTED_BIT │
          │  (BIT0)             │
          └─────────────────────┘
```

#### FreeRTOS Configuration

| Thông số | Giá trị |
|---|---|
| HZ (tick rate) | 100 Hz (10 ms/tick) |
| Số lõi CPU | 2 |
| Tick idle | CPU0 + CPU1 |
| Task name max length | 16 ký tự |
| Timer service priority | 1 |
| Timer task stack | 2048 |
| ISR stack | 1536 |
| Idle task stack | 1536 |
| Task notification entries | 1 |
| Stack overflow check | Canary (kiểm tra byte guard) |
| Queue registry size | 0 |

