#pragma once

#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"

// ============================================
// CẤU HÌNH PHẦN CỨNG - CẢM BIẾN GSR
// ============================================

// Chân ADC
#define GSR_PIN                 GPIO_NUM_5
#define GSR_ADC_UNIT            ADC_UNIT_1
#define GSR_ADC_CHANNEL         ADC_CHANNEL_4  // GPIO 4 trên ESP32-S3 = ADC1_CH3

// Tham số thuật toán
#define GSR_SAMPLE_SIZE         20
