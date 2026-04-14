# Hệ thống giám sát lưu lượng nước ESP32 — YF-S201 + PZEM-004T

## 1. Tổng quan

Dự án xây dựng một hệ thống nhúng trên **ESP32** đo lưu lượng nước và công suất điện, gửi dữ liệu lên **HiveMQ Cloud** qua MQTT. Hệ thống dùng FreeRTOS quản lý tác vụ, ESP-IDF làm framework, kiến trúc **component-based** với 6 component độc lập.

### Tính năng chính

- Đo lưu lượng nước tức thời (L/phút) qua cảm biến **YF-S201** (ISR GPIO)
- Đếm tổng thể tích nước đã chảy (Lít)
- Đo điện áp, dòng điện, công suất, năng lượng qua **PZEM-004T** (UART Modbus)
- Điều khiển relay bật/tắt từ xa qua MQTT
- Phát hiện rò rỉ nước (lưu lượng nhỏ nhưng liên tục)
- WiFi provisioning qua **SoftAP + Web Portal** (không cần cắm cáp)
- Đồng bộ thời gian qua **SNTP** (timezone ICT-7)
- Lưu trạng thái WiFi trên **NVS**
- Giao diện Serial Monitor in dữ liệu real-time

## 2. Kiến trúc hệ thống

```
EmbeddedWaterFlow/
├── CMakeLists.txt
├── sdkconfig
├── partitions.csv
├── main/
│   ├── main.c             # app_main(), monitor_task
│   ├── main.idf_component.yml
│   └── CMakeLists.txt
└── components/
    ├── water_data/          # Singleton struct + EventGroup
    │   ├── water_data.c
    │   ├── include/water_data.h
    │   └── CMakeLists.txt
    ├── water_flow_sensor/   # YF-S201 driver + ISR + FreeRTOS task
    │   ├── water_flow_sensor.c
    │   ├── include/water_flow_sensor.h
    │   ├── include/yfs201_config.h    # Hardware pins, thresholds
    │   └── CMakeLists.txt
    ├── pzem004t/            # PZEM-004T UART Modbus + FreeRTOS task
    │   ├── pzem004t.c
    │   ├── include/pzem004t.h
    │   ├── include/pzem004t_config.h  # UART pins, baud, interval
    │   └── CMakeLists.txt
    ├── wifi_manager/        # SoftAP + STA + HTTP server + NTP
    │   ├── wifi_manager.c
    │   ├── include/wifi_manager.h
    │   └── CMakeLists.txt
    ├── mqtt_manager/        # HiveMQ Cloud MQTT client + relay control
    │   ├── mqtt_manager.c
    │   ├── include/mqtt_manager.h
    │   ├── include/mqtt_config.h      # Broker URI, topics, credentials
    │   └── CMakeLists.txt
    └── relay_control/       # GPIO relay driver
        ├── relay_control.c
        ├── include/relay_control.h
        └── CMakeLists.txt
```

### Luồng dữ liệu

```
YF-S201 (GPIO ISR)
       │
       ▼
water_flow_sensor_task ──► water_sensor_data_t ◄── pzem004t_task
       │                          │
       │                          │
       └──────────────────────────┴──► monitor_task
                                          │
                                          ├──► Serial (printf)
                                          └──► mqtt_manager ──► HiveMQ Cloud
```

## 3. FreeRTOS Task Architecture

| Task | Priority | Stack | Chức năng | Đợi WiFi |
|------|----------|-------|-----------|----------|
| `water_flow_task` | 5 | 4096 | Đọc YF-S201, tính lưu lượng | Có |
| `pzem004t_task` | 5 | 4096 | Đọc PZEM-004T UART | Có |
| `mqtt_task` (internal) | 5 | 8192 | MQTT event loop (esp_mqtt) | Có |
| `monitor_task` | 3 | 4096 | Serial print, MQTT publish | Có |

- 3 task sensor ngang hàng priority 5 — scheduler chia CPU time-slice công bằng
- `monitor_task` priority 3 thấp hơn — chỉ chạy khi 3 task kia rảnh

### EventGroup đồng bộ

`WIFI_CONNECTED_BIT` (bit 0) được set khi ESP32 nhận IP từ AP. Mọi task sensor đều chờ bit này trước khi bắt đầu đọc cảm biến:

```c
xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
```

## 4. Cấu hình phần cứng

### 4.1 YF-S201 — Cảm biến lưu lượng nước

File: `components/water_flow_sensor/include/yfs201_config.h`

| Macro | Giá trị | Ý nghĩa |
|-------|---------|----------|
| `YFS201_SIGNAL_PIN` | GPIO_NUM_4 | Chân GPIO nhận xung |
| `YFS201_PULSES_PER_LITER` | 450.0f | Số xung / lít nước |
| `FLOW_CALC_PERIOD_MS` | 1000 | Chu kỳ tính lưu lượng |
| `FLOW_DETECT_THRESHOLD` | 0.1 L/min | Ngưỡng phát hiện dòng chảy |
| `FLOW_LEAK_THRESHOLD` | 2.0 L/min | Ngưỡng rò rỉ |
| `FLOW_CONFIRM_CYCLES` | 3 | Chu kỳ xác nhận dòng chảy |
| `FLOW_IDLE_CYCLES` | 5 | Chu kỳ không dòng → IDLE |

### 4.2 PZEM-004T — Đo điện năng

File: `components/pzem004t/include/pzem004t_config.h`

| Macro | Giá trị | Ý nghĩa |
|-------|---------|----------|
| `PZEM_UART_NUM` | UART_NUM_1 | UART1 |
| `PZEM_TX_PIN` | GPIO_NUM_25 | TX |
| `PZEM_RX_PIN` | GPIO_NUM_26 | RX |
| `PZEM_BAUD_RATE` | 9600 | Baud rate |
| `PZEM_DEFAULT_ADDR` | 0xF8 | Modbus address |
| `PZEM_READ_INTERVAL_MS` | 1000 | Chu kỳ đọc |
| `PZEM_MAX_RETRIES` | 3 | Số lần thử lại |
| `PZEM_UART_TIMEOUT_MS` | 500 | Timeout UART |

### 4.3 Relay

File: `components/relay_control/include/relay_control.h`

| Macro | Giá trị | Ý nghĩa |
|-------|---------|----------|
| `RELAY_GPIO_PIN` | 27 | GPIO điều khiển relay |

Relay hoạt động ở chế độ **active-low** (GPIO=0 → relay ON, GPIO=1 → relay OFF).

### 4.4 MQTT

File: `components/mqtt_manager/include/mqtt_config.h`

| Macro | Giá trị |
|-------|---------|
| `MQTT_BROKER_URI` | `mqtts://...s1.eu.hivemq.cloud:8883` |
| `MQTT_USERNAME` | `Cntt1234` |
| `MQTT_PASSWORD` | `Cntt1234` |
| `MQTT_PUB_TOPIC` | `waterflow/sensors/data` |
| `MQTT_RELAY_SUB_TOPIC` | `waterflow/relay/control` |
| `MQTT_RELAY_PUB_TOPIC` | `waterflow/relay/status` |

### 4.5 WiFi Provisioning

File: `components/wifi_manager/include/wifi_manager.h`

| Macro | Giá trị |
|-------|---------|
| `WATER_WIFI_AP_SSID` | `WaterFlow-Setup` |
| `WATER_WIFI_AP_PASSWORD` | (Open — không có mật khẩu) |
| `HTTP_PORT` | 80 |

## 5. MQTT Protocol

### 5.1 Sensor Data (publish — 1 giây)

Topic: `waterflow/sensors/data`

```json
{
  "timestamp": "2026-04-13T10:30:00Z",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "voltage": 220.5,
  "current": 1.234,
  "power": 271.8,
  "energy": 1.2345,
  "flow_rate": 2.50,
  "total_volume": 15.678,
  "pulse_count": 7055,
  "mode": "ACTIVE"
}
```

### 5.2 Relay Control (subscribe)

Topic: `waterflow/relay/control`

| Lệnh | Hành động |
|------|-----------|
| `{"relay":"ON"}` hoặc `"on"` | Bật relay |
| `{"relay":"OFF"}` hoặc `"off"` | Tắt relay |
| `{"relay":"TOGGLE"}` hoặc `"toggle"` | Đảo trạng thái relay |

### 5.3 Relay Status (publish)

Topic: `waterflow/relay/status`

```json
{"relay":"ON","mac_address":"AA:BB:CC:DD:EE:FF"}
```

## 6. Chế độ hoạt động

| Mode | Giá trị | Ý nghĩa |
|------|---------|----------|
| `FLOW_MODE_CONFIG` | 0 | Chưa cấu hình WiFi — SoftAP đang chạy |
| `FLOW_MODE_IDLE` | 1 | Không có nước chảy |
| `FLOW_MODE_ACTIVE` | 2 | Phát hiện dòng chảy bình thường (≥ 2 L/min) |
| `FLOW_MODE_LEAK` | 3 | Phát hiện rò rỉ (< 2 L/min nhưng liên tục) |

### Sơ đồ chuyển trạng thái

```
                    ┌──────────────┐
         ┌─────────→│   IDLE       │←──────────────┐
         │          │(khong co nuoc)│               │
         │          └──────┬───────┘               │
         │                 │ idle_cycles > 5        │
         │          ┌──────▼───────┐               │
         │  confirm 3 chu ky       │               │
         │ ┌─────────│   ACTIVE    │──────────────┤
         │ │         └─────────────┘              │
         │ │ (Q >= 2.0 L/min)                    │
         │ │                                      │
         │ │         ┌──────────────┐             │
         │ └────────→│    LEAK      │←────────────┘
         │  (Q < 2.0  │              │    (Q < 2.0 L/min
         │   L/min)   └──────────────┘     lien tuc)
```

## 7. Nguyên lý đo lưu lượng

Cảm biến YF-S201 sử dụng **bánh xe turbine** bên trong. Mỗi vòng quay tạo 1 xung vuông, tần số tỷ lệ tuyến tính với lưu lượng:

```
F(Hz) = 7.5 × Q(L/min)
Xung/Lít = 450
```

Công thức tính trong code:

```
Q(L/min) = (pulses × 60000) / (450 × period_ms)
```

- `60000`: đổi từ phút sang mili-giây
- `period_ms`: khoảng thời gian đo (mặc định 1000ms)

### Interrupt Service Routine

```
GPIO 4 (cạnh lên) ──→ flow_pulse_isr() [IRAM, ISR-safe]

portENTER_CRITICAL_ISR(&s_pulse_mutex)
  s_pulse_count_isr++
portEXIT_CRITICAL_ISR(&s_pulse_mutex)

portENTER_CRITICAL_ISR(&s_event_mutex)
  s_new_pulse_event = true
portEXIT_CRITICAL_ISR(&s_event_mutex)
```

## 8. WiFi Provisioning Flow

```
Khởi động
    │
    ├── Có WiFi trong NVS? ──→ Kết nối STA ──→ Nhận IP ──→ Bật MQTT
    │
    └── Chưa có? ──→ Phát SoftAP 'WaterFlow-Setup'
                       │
                       └──→ HTTP Server (port 80)
                                │
                                └──→ User nhập SSID/password trên Web Portal
                                         │
                                         └──→ Lưu NVS ──→ Restart ──→ Kết nối STA
```

- Truy cập `http://192.168.4.1` để cấu hình WiFi
- SSID WiFi: `WaterFlow-Setup` (open network)
- Sau khi nhấn "Kết Noi", ESP32 tự restart và kết nối

## 9. Cài đặt và biên dịch

### Yêu cầu

- **ESP-IDF** 4.4.x hoặc 5.x, đã thiết lập biến môi trường (`idf.py` có sẵn trong PATH)
- **Python** 3.8+
- **ESP32 DevKit** (bất kỳ module ESP32 nào)
- Cáp USB để flash firmware

### Các bước

**Bước 1:** Di chuyển vào thư mục dự án

```bash
cd d:/Documents/BTL/EmbeddedWaterFlow
```

**Bước 2:** Thiết lập target ESP32

```bash
idf.py set-target esp32
```

**Bước 3:** Cấu hình project (tùy chọn)

```bash
idf.py menuconfig
```

Kiểm tra:
- `Serial flasher config → Default serial port → COMx` (chọn cổng ESP32)
- `Component config → FreeRTOS → Kernel → configTICK_RATE_HZ → 1000`

**Bước 4:** Biên dịch

```bash
idf.py build
```

**Bước 5:** Flash và monitor

```bash
idf.py -p COM3 flash monitor
```

Thay `COM3` bằng cổng COM tương ứng.

## 10. Kết quả mong đợi

### Serial Output (115200 baud)

```
I (456) MAIN: ==========================================
I (457) MAIN:   Water Flow Sensor - YF-S201 + PZEM-004T
I (458) MAIN:   ESP32 WiFi Config via Web Portal
I (459) MAIN:   MQTT: HiveMQ Cloud
I (460) MAIN: ==========================================
I (461) MAIN: Khoi dong WiFi Provisioning...
I (468) WIFI_AP: SoftAP 'WaterFlow-Setup' dang phat song WiFi!
I (469) WIFI_AP: Vao 192.168.4.1 de cau hinh WiFi

[Sau khi ket noi WiFi thanh cong...]
I (520) WIFI_AP: Da ket noi WiFi - IP: 192.168.1.100
I (521) WIFI_AP: => Da co ket noi WiFi. Cac sensor bat dau hoat dong!
I (522) MQTT: MQTT client da khoi dong
I (530) YFS201: Water Flow Sensor Task Started...
I (535) PZEM004T: PZEM-004T Task Started...

========== Water Flow Monitor ==========
  Mode:    IDLE
  MAC:     AA:BB:CC:DD:EE:FF
  --- YF-S201 ---
  Flow:    0.00 L/min
  Total:   0.000 L
  Pulses:  0
  --- PZEM-004T ---
  Voltage: 220.5 V
  Current: 0.000 A
  Power:   0.0 W
  Energy:  0.0000 kWh
  --- Relay ---
  State:   OFF
==========================================

[Bat dau co nuoc chay...]
I (1530) YFS201: Flow: 1.53 L/min | Total: 0.025 L | Pulses: 7 | Mode: 1
I (2530) YFS201: Flow: 2.50 L/min | Total: 0.065 L | Pulses: 11 | Mode: 2

I (2530) MQTT: Nhan du lieu MQTT: topic='waterflow/relay/control'
I (2531) MQTT: Relay command: {"relay":"ON"}
I (2531) RELAY: Relay ON
I (2532) MQTT: Pub relay status: {"relay":"ON","mac_address":"AA:BB:CC:DD:EE:FF"}

[Phat hien ro ri...]
I (8530) YFS201: PHAT HIEN RO RI! Luu luong: 0.50 L/min
```

## 11. Sơ đồ đấu dây

### YF-S201

```
  ESP32                     YF-S201
  ───────────               ───────────────
  5V / Vin     ────────────  Dây Đỏ (VCC)
  GND          ────────────  Dây Đen (GND)
  GPIO 4       ────────────  Dây Vàng (Signal)
```

### PZEM-004T (kết nối qua MAX-485 hoặc module TTL)

```
  ESP32                     PZEM-004T
  ───────────               ───────────────
  GPIO 25 (TX)  ────────────  RX (TTL module)
  GPIO 26 (RX)  ────────────  TX (TTL module)
  GND           ────────────  GND
  5V            ────────────  VCC (5V)
```

### Relay Module

```
  ESP32                     Relay Module (5V)
  ───────────               ───────────────
  GPIO 27      ────────────  IN (Signal)
  GND           ────────────  GND
  5V            ────────────  VCC
```

> **Lưu ý:** Relay trong hệ thống hoạt động ở chế độ **active-low** — relay ON khi GPIO=0, OFF khi GPIO=1.

## 12. Các lệnh MQTT thường dùng (HiveMQ Cloud)

### Bật relay

```bash
mosquitto_pub -h eaa56c03c1bd4c0194b2fb3dd11cfe4a.s1.eu.hivemq.cloud \
  -p 8883 --capath /etc/ssl/certs/ -u Cntt1234 -P Cntt1234 \
  -t waterflow/relay/control -m '{"relay":"ON"}'
```

### Tắt relay

```bash
mosquitto_pub -h eaa56c03c1bd4c0194b2fb3dd11cfe4a.s1.eu.hivemq.cloud \
  -p 8883 --capath /etc/ssl/certs/ -u Cntt1234 -P Cntt1234 \
  -t waterflow/relay/control -m '{"relay":"OFF"}'
```

### Đảo relay

```bash
mosquitto_pub -h eaa56c03c1bd4c0194b2fb3dd11cfe4a.s1.eu.hivemq.cloud \
  -p 8883 --capath /etc/ssl/certs/ -u Cntt1234 -P Cntt1234 \
  -t waterflow/relay/control -m '{"relay":"TOGGLE"}'
```

