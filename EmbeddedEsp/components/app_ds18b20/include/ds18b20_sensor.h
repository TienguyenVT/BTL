#pragma once
#include "driver/gpio.h"

/**
 * DS18B20 Wrapper API — giữ nguyên interface cũ cho main.c
 * Bên dưới sử dụng ESP-IDF onewire_bus RMT driver (non-blocking)
 */
void ds18b20_sensor_init(gpio_num_t pin);
float ds18b20_sensor_get_temp(void);
