/**
 * DHT11 Driver — Microsecond-precise GPIO polling
 * Single-wire protocol with esp_timer for accurate timing
 */

#include "dht11_sensor.h"
#include "dht11_config.h"
#include "health_data.h"
#include "thermal_processor.h"

#include "esp_log.h"
#include "driver/gpio.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "DHT11";

// Trạng thái toàn cục
static volatile int s_consecutive_fails = 0;

/**
 * Chờ GPIO level với microsecond timing (tối ưu hóa tốc độ)
 * @param level: GPIO level cần chờ (0 or 1)
 * @param timeout_us: Timeout bằng microseconds
 * @return true nếu thành công, false nếu timeout
 */
static bool dht11_wait_level(int level, uint32_t timeout_us) {
    int64_t start_time_us = esp_timer_get_time();
    
    while (gpio_get_level(DHT11_PIN) != level) {
        if ((esp_timer_get_time() - start_time_us) > (int64_t)timeout_us) {
            return false;
        }
    }
    
    return true;
}

/**
 * Đọc một bit từ DHT11 với microsecond precision
 */
static int dht11_read_bit(void) {
    // 1. Chờ xung LOW bắt đầu bit (50µs)
    if (!dht11_wait_level(0, 200)) {
        return -1;
    }

    // 2. Chờ xung HIGH bắt đầu dữ liệu
    if (!dht11_wait_level(1, 200)) {
        return -1;
    }

    // 3. Đo độ dài xung HIGH
    int64_t start_time_us = esp_timer_get_time();
    
    // 4. Chờ xung LOW kết thúc dữ liệu
    if (!dht11_wait_level(0, 200)) {
        return -1;
    }
    
    int64_t pulse_duration_us = esp_timer_get_time() - start_time_us;

    // Bit 0: ~26-28µs, Bit 1: ~70µs. Ngưỡng ~40µs
    return (pulse_duration_us > 40) ? 1 : 0;
}

/**
 * Đọc byte (8 bits) từ DHT11
 */
static int dht11_read_byte(void) {
    int byte = 0;
    for (int i = 0; i < 8; i++) {
        int bit = dht11_read_bit();
        if (bit < 0) {
            return -1;
        }
        byte = (byte << 1) | (bit & 0x01);
    }
    return byte;
}

void dht11_sensor_init(gpio_num_t pin) {
    ESP_LOGI(TAG, "Khoi tao DHT11 tren GPIO %d...", pin);

    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << pin),
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

    // Đưa line lên HIGH (idle state)
    gpio_set_level(pin, 1);

    vTaskDelay(pdMS_TO_TICKS(1000));
    ESP_LOGI(TAG, "DHT11 initialized successfully");
}

dht11_reading_t dht11_sensor_read(void) {
    dht11_reading_t result = { .humidity = 0, .temperature = 0, .is_valid = false };

    // ====================================================================
    // PHASE 1: Gửi start signal (cần vTaskDelay nên PHẢI ngoài critical)
    // ====================================================================
    gpio_set_direction(DHT11_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(DHT11_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(20));  // Low pulse >=18ms

    // ====================================================================
    // PHASE 2: Vào Critical Section TRƯỚC KHI thả line
    //          → Loại bỏ hoàn toàn khe hở timing
    // ====================================================================
    portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
    portENTER_CRITICAL(&mux);

    // Thả line HIGH 20-40µs rồi chuyển input
    gpio_set_level(DHT11_PIN, 1);
    esp_rom_delay_us(30);
    gpio_set_direction(DHT11_PIN, GPIO_MODE_INPUT);

    // Chờ DHT kéo LOW (response 80µs)
    if (!dht11_wait_level(0, 200)) {
        portEXIT_CRITICAL(&mux);
        ESP_LOGW(TAG, "No DHT11 response (LOW timeout)");
        s_consecutive_fails++;
        return result;
    }

    // Chờ DHT kéo HIGH (response 80µs)
    if (!dht11_wait_level(1, 200)) {
        portEXIT_CRITICAL(&mux);
        ESP_LOGW(TAG, "No DHT11 response (HIGH timeout)");
        s_consecutive_fails++;
        return result;
    }

    // ====================================================================
    // PHASE 3: Đọc 40 bits (5 bytes) trong critical section
    // ====================================================================
    uint8_t data[5] = {0};
    for (int i = 0; i < 5; i++) {
        int byte = dht11_read_byte();
        if (byte < 0) {
            portEXIT_CRITICAL(&mux);
            ESP_LOGW(TAG, "Failed to read byte %d", i);
            s_consecutive_fails++;
            return result;
        }
        data[i] = (uint8_t)byte;
    }

    portEXIT_CRITICAL(&mux);

    // ====================================================================
    // PHASE 4: Checksum (ngoài critical section)
    // ====================================================================
    uint8_t checksum_calc = (data[0] + data[1] + data[2] + data[3]) & 0xFF;
    if (checksum_calc != data[4]) {
        ESP_LOGW(TAG, "Checksum error: calc=0x%02x, expected=0x%02x", checksum_calc, data[4]);
        s_consecutive_fails++;
        return result;
    }

    result.humidity = data[0];
    result.temperature = data[2];
    result.is_valid = true;
    s_consecutive_fails = 0;
    return result;
}

// --- FREERTOS TASK ---
void dht11_sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "DHT11 Sensor Task Started...");

    dht11_sensor_init(DHT11_PIN);
    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    static TickType_t last_read_tick = 0;
    const TickType_t MIN_INTERVAL = pdMS_TO_TICKS(2000);  // ≥2s guard (Vấn đề 4)

    while (1) {
        // Chờ WiFi kết nối (như các sensor khác)
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        // Timing guard: đảm bảo tối thiểu 2s giữa các lần đọc (Vấn đề 4)
        TickType_t now = xTaskGetTickCount();
        if (last_read_tick != 0 && (now - last_read_tick) < MIN_INTERVAL) {
            vTaskDelay(MIN_INTERVAL - (now - last_read_tick));
        }
        last_read_tick = xTaskGetTickCount();

        dht11_reading_t reading = dht11_sensor_read();

        if (reading.is_valid) {
            // Cập nhật humidity
            data->humidity = reading.humidity;

            // Cập nhật raw temperature (debug)
            data->dht11_temperature = (float)reading.temperature;

            // EMA filter cho ambient_temp (α=0.2, Vấn đề 5)
            data->ambient_temp = DHT11_AMBIENT_EMA_ALPHA * (float)reading.temperature
                               + (1.0f - DHT11_AMBIENT_EMA_ALPHA) * data->ambient_temp;
        } else {
            ESP_LOGW(TAG, "DHT11 read failed (attempt %d)", s_consecutive_fails);
            if (s_consecutive_fails > DHT11_MAX_CONSECUTIVE_FAILS) {
                // Reset nếu lỗi quá nhiều lần
                ESP_LOGI(TAG, "Resetting DHT11 after too many failures...");
                dht11_sensor_init(DHT11_PIN);
                s_consecutive_fails = 0;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(DHT11_POLL_INTERVAL_MS));
    }
}