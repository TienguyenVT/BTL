#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "driver/gpio.h"

/**
 * Kết quả đọc từ DHT11 (humidity + temperature)
 */
typedef struct {
    uint8_t humidity;        // 0-100 (%)
    uint8_t temperature;     // 0-50 (°C)
    bool is_valid;           // true nếu dữ liệu hợp lệ
} dht11_reading_t;

/**
 * Khởi tạo DHT11 trên GPIO
 */
void dht11_sensor_init(gpio_num_t pin);

/**
 * Đọc dữ liệu từ DHT11 (blocking ~20ms)
 * @return dht11_reading_t với is_valid=true nếu thành công
 */
dht11_reading_t dht11_sensor_read(void);

/**
 * FreeRTOS task function
 */
void dht11_sensor_task(void *pvParameters);