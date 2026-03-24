#pragma once

#include "driver/i2c.h"

// ============================================
// CẤU HÌNH PHẦN CỨNG - MÀN HÌNH OLED SSD1306
// ============================================

// Chân I2C (bus I2C_NUM_0)
#define SSD1306_SDA_PIN         GPIO_NUM_6
#define SSD1306_SCL_PIN         GPIO_NUM_7
#define SSD1306_I2C_PORT        I2C_NUM_0
#define SSD1306_I2C_SPEED       400000

// Địa chỉ I2C
#define SSD1306_I2C_ADDRESS     0x3C
