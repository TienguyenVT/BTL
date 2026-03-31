#pragma once

#include "driver/i2c.h"
#include "driver/gpio.h"

// ============================================
// CẤU HÌNH PHẦN CỨNG - CẢM BIẾN MAX30105
// ============================================

// Chân I2C (bus riêng I2C_NUM_1)
#define MAX30105_SDA_PIN        GPIO_NUM_12
#define MAX30105_SCL_PIN        GPIO_NUM_13
#define MAX30105_I2C_PORT       I2C_NUM_1
#define MAX30105_I2C_SPEED      400000

// Chân ngắt (interrupt)
#define MAX30105_INT_PIN        GPIO_NUM_11

// Địa chỉ I2C
#define MAX30105_ADDRESS        0x57
