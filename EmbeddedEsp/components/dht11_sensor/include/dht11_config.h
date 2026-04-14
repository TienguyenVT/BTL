#pragma once

// ============================================
// CẤU HÌNH PHẦN CỨNG - CẢM BIẾN DHT11
// ============================================

// Chân Data (single wire, bidirectional)
#define DHT11_PIN               4
#define DHT11_I2C_PULLUP        true

// Tham số timing (µs) — DHT11 datasheet
#define DHT11_STARTUP_TIME_MS   1000    // Chờ DHT stable
#define DHT11_REQUEST_PULSE_MS  18      // Host gửi low pulse (18ms)
#define DHT11_RESPONSE_TIMEOUT  100     // Timeout chờ response (100µs)
#define DHT11_BIT_TIMEOUT       200     // Timeout per bit (200µs)
#define DHT11_POLL_INTERVAL_MS  2000    // Polling interval (2s)

// Data valid range
#define DHT11_MAX_CONSECUTIVE_FAILS 5   // Reset after 5 fails