#ifndef __SENSOR_HUB_H__
#define __SENSOR_HUB_H__

#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

// Include cấu hình phần cứng từ từng module
#include "max30105_config.h"
#include "ssd1306_config.h"

// Mutex bảo vệ bus I2C (mỗi bus 1 mutex nếu cần)
extern SemaphoreHandle_t i2c_mutex;

// Khởi tạo tất cả bus I2C master (gọi 1 lần trong app_main)
void sensor_hub_i2c_init(void);

// FreeRTOS task function — đọc MAX30105, tính BPM/SpO2, cập nhật health_data
void sensor_hub_task(void *pvParameters);

#endif // __SENSOR_HUB_H__

