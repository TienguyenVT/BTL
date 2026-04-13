# Hệ thống đo lưu lượng nước YF-S201 trên ESP32

## 1. Tổng quan

Dự án này xây dựng một hệ thống nhúng trên ESP32 (ESP32-WROOM-32) để đọc và xử lý dữ liệu từ cảm biến lưu lượng nước **YF-S201**. Hệ thống được phát triển theo kiến trúc **component-based** (dựa trên EmbeddedEsp - một hệ thống nhúng IoMT chuẩn), sử dụng FreeRTOS để quản lý tác vụ và ESP-IDF làm framework.

### 1.1 Tính năng chính

- Đo lưu lượng nước tức thời (L/phút)
- Đếm tổng thể tích nước đã chảy (Lít)
- Phát hiện dòng chảy / không dòng chảy
- Phát hiện rò rỉ (lưu lượng nhỏ nhưng liên tục)
- Giao diện Serial để xem dữ liệu
- Lưu trạng thái trên NVS (Non-Volatile Storage)

### 1.2 Kiến trúc hệ thống

```
EmbeddedWaterFlow/
├── CMakeLists.txt                    # Project entry (idf-build)
├── sdkconfig                         # ESP-IDF configuration (ESP32 target)
├── partitions.csv                    # Bảng phân vùng flash
├── main/
│   ├── main.c                        # app_main() + monitor_task
│   └── CMakeLists.txt                # Component registration (explicit SRCS)
└── components/
    ├── water_data/                   # Shared data structure + EventGroup
    │   ├── water_data.c
    │   ├── water_data.h
    │   └── CMakeLists.txt
    └── water_flow_sensor/            # YF-S201 driver + FreeRTOS task
        ├── water_flow_sensor.c       # ISR + flow calculation
        ├── water_flow_sensor.h
        ├── include/
        │   ├── yfs201_config.h       # Hardware & algorithm config
        │   └── water_flow_sensor.h
        └── CMakeLists.txt
```

## 2. Cài đặt và biên dịch

### 2.1 Yêu cầu

- **ESP-IDF** (phiên bản 4.4.x hoặc 5.x) đã được cài đặt và thiết lập biến môi trường.
- **Python** 3.8 trở lên.
- **ESP32 DevKit** (ESP32-WROOM-32 hoặc tương đương).
- Cáp USB để flash firmware.

### 2.2 Các bước cài đặt

**Bước 1:** Di chuyển vào thư mục dự án

```bash
cd C:/Documents/BTL/EmbeddedWaterFlow
```

**Bước 2:** Thiết lập mục tiêu ESP32

```bash
idf.py set-target esp32
```

**Bước 3:** Cấu hình project (tùy chọn)

```bash
idf.py menuconfig
```

Kiểm tra các thông số:
- Serial flasher config → Default serial port → COMx (chọn cổng ESP32)
- Component config → FreeRTOS → Kernel → configTICK_RATE_HZ → 1000

**Bước 4:** Biên dịch project

```bash
idf.py build
```

**Bước 5:** Flash firmware vào ESP32

```bash
idf.py -p COM3 flash monitor
```

Thay `COM3` bằng cổng COM tương ứng của ESP32.

**Bước 6:** Mở Serial Monitor

```bash
idf.py monitor
```

Hoặc kết hợp (đã làm ở bước 5).

## 3. Nguyên lý hoạt động

### 3.1 Nguyên lý đo lưu lượng

Cảm biến YF-S201 sử dụng **bánh xe turbine (turbine wheel)** bên trong. Khi nước chảy qua:

1. Bánh xe turbine quay với tốc độ tỷ lệ với lưu lượng.
2. Mỗi vòng quay tạo ra **1 xung vuông (square wave)**.
3. Tần số xung tỷ lệ tuyến tính với lưu lượng:

```
F(Hz) = 7.5 × Q(L/min)
```

4. Mỗi **lít nước** tương ứng với **450 xung**.

```
Xung/Lít = 450
```

### 3.2 Tính lưu lượng trong code

```
Q(L/min) = (số_xung × 60000) / (PULSES_PER_LITER × chu_kỳ_ms)
         = xung × 133.33... / chu_kỳ_ms
```

- `60000`: đổi từ phút sang mili-giây
- `450`: số xung trên mỗi lít nước
- `chu_kỳ_ms`: khoảng thời gian đo (1 giây = 1000ms)

### 3.3 Interrupt Service Routine (ISR)

```
┌─────────────────────────────────────────────────────────┐
│  GPIO 4 (cạnh lên) ──→ ISR: flow_pulse_isr()          │
│                                                         │
│  ISR thực hiện:                                         │
│    1. Tăng biến đếm xung (s_pulse_count_isr++)          │
│    2. Đặt cờ s_new_pulse_event = true                  │
│                                                         │
│  Cờ có thể được reset bởi task chính sau khi đọc      │
└─────────────────────────────────────────────────────────┘
```

### 3.4 Sơ đồ trạng thái

```
                    ┌──────────────┐
         ┌─────────→│   IDLE       │←─────────────┐
         │          │(khong co nuoc)│              │
         │          └──────┬───────┘              │
         │                 │ so chu ky > 5        │
         │          ┌──────▼───────┐              │
         │   confirm 3 chu ky    │              │
         │ ┌─────────│   ACTIVE    │────────────┤
         │ │         └─────────────┘              │
         │ │ (luu luong >= 0.1 L/min)             │
         │ │                                      │
         │ │         ┌──────────────┐             │
         │ └────────→│    LEAK      │←────────────┘
         │  (Q < 2.0  │  (ro ri nuoc)│   (Q < 2.0 L/min
         │   L/min)   └──────────────┘    lien tuc)
         │                 │
         └─────────────────┘
```

## 4. Cấu hình thông số

Tất cả thông số hardware và thuật toán được định nghĩa trong file:

```
components/water_flow_sensor/include/yfs201_config.h
```

### Các thông số có thể tùy chỉnh

| Thông số | Giá trị mặc định | Ý nghĩa |
|----------|-------------------|---------|
| `YFS201_SIGNAL_PIN` | GPIO_NUM_4 | Chân GPIO nhận xung |
| `YFS201_PULSES_PER_LITER` | 450.0f | Số xung / lít nước |
| `FLOW_CALC_PERIOD_MS` | 1000 | Chu kỳ tính lưu lượng (ms) |
| `FLOW_DETECT_THRESHOLD` | 0.1 | Ngưỡng phát hiện dòng chảy (L/min) |
| `FLOW_LEAK_THRESHOLD` | 2.0 | Ngưỡng rò rỉ (L/min) |
| `FLOW_CONFIRM_CYCLES` | 3 | Số chu kỳ xác nhận dòng chảy |
| `FLOW_IDLE_CYCLES` | 5 | Số chu kỳ không dòng → IDLE |

## 5. Kết quả mong đợi

### Serial Output (115200 baud)

```
I (456) MAIN: ==============================
I (457) MAIN:   Water Flow Sensor - YF-S201
I (458) MAIN:   ESP32 Target Build
I (459) MAIN: ==============================
I (461) MAIN: System started. Cho dong nuoc...
I (467) YFS201: Khoi tao YF-S201 tren GPIO 4...
I (468) YFS201: YF-S201 ready. VCC=5V, Signal=GPIO4, GND=GND
I (469) YFS201: Thong so: 450 xung/L, chu ky tinh=1.0s, nguong=0.10 L/min
I (472) YFS201: Water Flow Sensor Task Started...
I (525) YFS201: Flow: 0.00 L/min | Total: 0.000 L | Pulses: 0 | Mode: 0
[Bat dau co nuoc chay...]
I (1525) YFS201: Flow: 1.53 L/min | Total: 0.025 L | Pulses: 7 | Mode: 1
I (2525) YFS201: Flow: 2.10 L/min | Total: 0.060 L | Pulses: 9 | Mode: 1
```

### Các chế độ hoạt động

| Mode | Giá trị | Ý nghĩa |
|------|---------|----------|
| `IDLE` | 0 | Không có nước chảy |
| `ACTIVE` | 1 | Phát hiện dòng chảy bình thường |
| `LEAK` | 2 | Phát hiện rò rỉ |

## 6. Sơ đồ đấu dây chi tiết

Xem file: `docs/wiring.md`

```
  ESP32                    YF-S201
  ───────────              ───────────────
  5V / Vin    ────────────  Dây Đỏ (VCC)
  GND         ────────────  Dây Đen (GND)
  GPIO 4      ────────────  Dây Vàng (Signal)
```

## 7. So sánh với EmbeddedEsp

| Khía cạnh | EmbeddedEsp (IoMT) | EmbeddedWaterFlow (YF-S201) |
|-----------|---------------------|------------------------------|
| Chip | ESP32-S3 | ESP32 (WROOM-32) |
| Cảm biến | MAX30105, GSR, DS18B20, DHT11 | YF-S201 |
| Giao diện | I2C, ADC, OneWire, Interrupt | Interrupt (GPIO) |
| Task count | 6 tasks | 2 tasks |
| Cấu trúc dữ liệu | `health_data_t` (phức tạp) | `water_sensor_data_t` (đơn giản) |
| Component count | 10 components | 2 components |
| WiFi/MQTT | Có | Chưa tích hợp |
| Display | OLED SSD1306 | Không |

## 8. Hạn chế và hướng phát triển

### Hạn chế hiện tại
- Chưa tích hợp WiFi/MQTT để gửi dữ liệu lên cloud.
- Chưa có giao diện hiển thị (OLED).
- Chưa có cơ chế hiệu chuẩn (calibration) cho cảm biến.

### Hướng phát triển tiếp theo
1. Tích hợp WiFi + MQTT (tham khảo `wifi_manager` và `mqtt_manager` từ EmbeddedEsp).
2. Thêm OLED SSD1306 để hiển thị lưu lượng real-time.
3. Tích hợp cảm biến DHT11 để đo nhiệt độ và độ ẩm môi trường.
4. Thêm chức năng cảnh báo rò rỉ qua còi buzzer hoặc LED.
5. Tích hợp Deep Sleep để tiết kiệm năng lượng.
