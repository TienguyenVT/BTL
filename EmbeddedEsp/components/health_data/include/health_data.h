#ifndef __HEALTH_DATA_H__
#define __HEALTH_DATA_H__

#include <stdbool.h>
#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

// Bit dùng chung cho tất cả các module: chờ WiFi kết nối mới cho phép chạy
#define WIFI_CONNECTED_BIT BIT0

// 3 chế độ hoạt động của hệ thống
typedef enum {
    MODE_CONFIG,    // Đang chờ cấu hình WiFi
    MODE_IDLE,      // User không sử dụng thiết bị
    MODE_ACTIVE     // User đang đo sức khỏe
} system_mode_t;

// Struct tập trung dữ liệu của toàn bộ hệ thống
typedef struct {
    // Dữ liệu cảm biến
    int bpm;
    int spo2;
    int gsr;
    float body_temp;
    float room_temp;

    // Trạng thái hệ thống
    system_mode_t mode;
    bool is_user_present;
    float temp_baseline;    // Nhiệt độ phòng baseline (trước khi user chạm)
} health_data_t;

// Trả về con trỏ tới struct dữ liệu toàn cục (singleton)
health_data_t *health_data_get(void);

// Trả về EventGroupHandle dùng chung (tạo bởi main)
EventGroupHandle_t health_data_get_event_group(void);

// Phải gọi 1 lần duy nhất trong app_main()
void health_data_init(void);

#endif // __HEALTH_DATA_H__
