#ifndef __HEALTH_DATA_H__
#define __HEALTH_DATA_H__

#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

// Bit dùng chung cho tất cả các module: chờ WiFi kết nối mới cho phép chạy
#define WIFI_CONNECTED_BIT BIT0

// 4 chế độ hoạt động của hệ thống
typedef enum {
    MODE_CONFIG,    // Đang chờ cấu hình WiFi
    MODE_IDLE,      // User không sử dụng thiết bị
    MODE_ACTIVE,    // User đang đo sức khỏe
    MODE_CALIBRATE  // Admin hiệu chuẩn GSR về baseline 2200 bằng biến trở
} system_mode_t;

// Chất lượng phép đo nhiệt độ cơ thể
typedef enum {
    MEAS_QUALITY_INVALID = 0,   // T_skin ngoài range sinh lý
    MEAS_QUALITY_UNSTABLE,      // T_skin đang thay đổi nhanh (chưa cân bằng)
    MEAS_QUALITY_GOOD,          // Đo tin cậy
} measurement_quality_t;

// Struct tập trung dữ liệu của toàn bộ hệ thống
typedef struct {
    // Dữ liệu cảm biến
    int bpm;
    int spo2;
    int gsr;
    float body_temp;
    float room_temp;
    int humidity;              // 0-100 (%)

    // Dual-sensor fusion data
    float ambient_temp;        // DHT11 EMA-filtered ambient temperature
    float dht11_temperature;   // DHT11 raw temperature (debug)
    float dht11_bias;          // Learned bias correction (debug)
    uint8_t measurement_confidence; // 0=invalid, 50=unstable, 100=stable+validated
    measurement_quality_t measurement_quality;

    // GSR calibration (personal baseline)
    int32_t gsr_raw;             // Giá trị GSR thô từ ADC
    int32_t gsr_baseline;        // Baseline mà admin set = 2200 (cố định)
    int32_t gsr_offset;          // Offset = gsr_baseline - gsr_raw (khi calibrate)

    // Trạng thái hệ thống
    system_mode_t mode;
    bool is_user_present;
    float temp_baseline;    // Nhiệt độ phòng baseline (trước khi user chạm)

    // Calibrate state
    bool calibrate_active;  // true khi đang ở chế độ calibrate
    bool calibrate_done;    // true khi đã calibrate xong
} health_data_t;

// Trả về con trỏ tới struct dữ liệu toàn cục (singleton)
health_data_t *health_data_get(void);

// Trả về EventGroupHandle dùng chung (tạo bởi main)
EventGroupHandle_t health_data_get_event_group(void);

// Phải gọi 1 lần duy nhất trong app_main()
void health_data_init(void);

#endif // __HEALTH_DATA_H__
