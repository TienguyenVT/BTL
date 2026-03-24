#pragma once

#include "driver/gpio.h"

// ============================================
// CẤU HÌNH PHẦN CỨNG - CẢM BIẾN NHIỆT ĐỘ DS18B20
// ============================================

// Chân Data (OneWire)
#define DS18B20_PIN             GPIO_NUM_3

// Hệ số hiệu chỉnh nhiệt độ
#define DS18B20_TEMP_OFFSET         4.5f
#define DS18B20_TEMP_MULTIPLIER     1.0f
#define DS18B20_SMOOTH_SAMPLES      2
#define DS18B20_PREDICT_FACTOR      3.0f
