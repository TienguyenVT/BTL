/**
 * DS18B20 Driver — RMT-based (non-blocking)
 * Sử dụng ESP-IDF onewire_bus component thay cho bit-bang.
 * Không dùng portENTER_CRITICAL → không block interrupt/scheduler.
 */
#include "ds18b20_sensor.h"
#include "ds18b20_config.h"

// ESP-IDF component headers (espressif/onewire_bus + espressif/ds18b20)
#include "onewire_bus.h"
#include "onewire_bus_impl_rmt.h"
#include "ds18b20.h"       // This now pulls from espressif/ds18b20 correctly
#include "ds18b20_types.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "DS18B20";
static ds18b20_device_handle_t s_ds18b20_handle = NULL;
static onewire_bus_handle_t s_onewire_bus = NULL;

void ds18b20_sensor_init(gpio_num_t pin) {
    // 1. Tạo bus 1-Wire qua RMT peripheral (hardware timing, zero CPU blocking)
    onewire_bus_config_t bus_config = {
        .bus_gpio_num = pin,
    };
    onewire_bus_rmt_config_t rmt_config = {
        .max_rx_bytes = 10,
    };

    esp_err_t ret = onewire_new_bus_rmt(&bus_config, &rmt_config, &s_onewire_bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create 1-Wire RMT bus on GPIO%d: %s", pin, esp_err_to_name(ret));
        return;
    }

    // 2. Tìm DS18B20 trên bus (enumerate)
    onewire_device_iter_handle_t iter = NULL;
    ret = onewire_new_device_iter(s_onewire_bus, &iter);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create device iterator: %s", esp_err_to_name(ret));
        return;
    }

    onewire_device_t device;
    int device_count = 0;
    while (onewire_device_iter_get_next(iter, &device) == ESP_OK) {
        ds18b20_config_t ds_cfg = {};
        if (ds18b20_new_device_from_enumeration(&device, &ds_cfg, &s_ds18b20_handle) == ESP_OK) {
            ESP_LOGI(TAG, "DS18B20 #%d found on GPIO%d (RMT mode, non-blocking)", ++device_count, pin);
            ds18b20_set_resolution(s_ds18b20_handle, DS18B20_RESOLUTION_12B);
            break; // Chỉ sử dụng sensor đầu tiên
        }
    }
    onewire_del_device_iter(iter);

    if (s_ds18b20_handle == NULL) {
        ESP_LOGE(TAG, "No DS18B20 found on GPIO%d. Check wiring and pull-up resistor!", pin);
    }
}

float ds18b20_sensor_get_temp(void) {
    if (s_ds18b20_handle == NULL) {
        return -999.0f;
    }

    esp_err_t ret = ds18b20_trigger_temperature_conversion_for_all(s_onewire_bus);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Temperature conversion failed: %s", esp_err_to_name(ret));
        return -999.0f;
    }

    // Chờ 750ms cho quá trình convert (12-bit) — task sleep nhường CPU cho các task khác
    vTaskDelay(pdMS_TO_TICKS(750));

    float temp_c = 0.0f;
    ret = ds18b20_get_temperature(s_ds18b20_handle, &temp_c);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Temperature read failed: %s", esp_err_to_name(ret));
        return -999.0f;
    }

    return temp_c;
}
