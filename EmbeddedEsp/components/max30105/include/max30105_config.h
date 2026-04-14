#pragma once

// ============================================
// CẤU HÌNH PHẦN CỨNG - CẢM BIẾN MAX30105
// ============================================

// Chân I2C (bus riêng I2C_NUM_1)
#define MAX30105_SDA_PIN        12
#define MAX30105_SCL_PIN        13
#define MAX30105_I2C_PORT       1
#define MAX30105_I2C_SPEED      400000

// Chân ngắt (interrupt)
#define MAX30105_INT_PIN        11

// Địa chỉ I2C
#define MAX30105_ADDRESS        0x57
