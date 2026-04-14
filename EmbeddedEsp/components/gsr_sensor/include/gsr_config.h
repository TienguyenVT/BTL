#pragma once

// ============================================
// CẤU HÌNH PHẦN CỨNG - CẢM BIẾN GSR
// ============================================

// Chân ADC cho cảm biến GSR
#define GSR_PIN                 4
#define GSR_ADC_UNIT            1
#define GSR_ADC_CHANNEL         3  // GPIO 4 trên ESP32-S3 = ADC1_CH3

// Tham số thuật toán
#define GSR_SAMPLE_SIZE         20

// Baseline cố định mà admin set cho tất cả user
#define GSR_TARGET_BASELINE     2200

// Nút nhấn calibrate (GPIO 0 = BOOT button trên ESP32-S3)
#define CAL_BUTTON_PIN          0
#define CAL_BUTTON_PRESS_MS     3000   // Nhấn giữ 3 giây để xác nhận calibrate
