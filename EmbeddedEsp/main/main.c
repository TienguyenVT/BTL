#include "esp_log.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include "esp_sntp.h"

// --- Các module tự viết ---
#include "health_data.h"
#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "gsr_sensor.h"
#include "sensor_hub.h"
#include "ssd1306.h"
#include "ds18b20.h"
#include "ds18b20_config.h"
#include "ptit_logo.h"

static const char *TAG = "MAIN";

// --- SNTP ---
static void sntp_init_time(void) {
    ESP_LOGI(TAG, "Khoi tao SNTP de dong bo gio...");
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "pool.ntp.org");
    esp_sntp_init();

    // Set timezone UTC+7 (Vietnam)
    setenv("TZ", "ICT-7", 1);
    tzset();
}

// --- DS18B20 TASK ---
void ds18b20_task(void *pvParameters) {
    ESP_LOGI(TAG, "DS18B20 Task Started...");
    ds18b20_init(DS18B20_PIN);

    float temp_buffer[DS18B20_SMOOTH_SAMPLES] = {0};
    int sample_index = 0;
    int valid_count = 0;
    float prev_avg = 0;

    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    while (1) {
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        float raw_temp = ds18b20_get_temp();
        if (raw_temp > -100.0) {
            temp_buffer[sample_index] = raw_temp;
            sample_index = (sample_index + 1) % DS18B20_SMOOTH_SAMPLES;
            if (valid_count < DS18B20_SMOOTH_SAMPLES) valid_count++;

            float sum = 0;
            for (int i = 0; i < valid_count; i++) {
                sum += temp_buffer[i];
            }
            float avg_temp = sum / valid_count;

            if (data->is_user_present) {
                float derivative = 0;
                if (valid_count >= DS18B20_SMOOTH_SAMPLES && prev_avg > 0) {
                    derivative = avg_temp - prev_avg;
                }
                float boosted_temp = avg_temp + (derivative * DS18B20_PREDICT_FACTOR);
                data->body_temp = (boosted_temp * DS18B20_TEMP_MULTIPLIER) + DS18B20_TEMP_OFFSET;
            } else {
                data->room_temp = avg_temp;
            }

            prev_avg = avg_temp;
        } else {
            ESP_LOGW(TAG, "Loi doc DS18B20 (kiem tra day noi hoac dien tro keo)");
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

// --- DISPLAY TASK (UI thay đổi theo Mode) ---
void display_task(void *pvParameters) {
    ssd1306_t dev;
    ssd1306_init(&dev, SSD1306_I2C_PORT);

    char buf[32];
    health_data_t *data = health_data_get();
    system_mode_t prev_mode = -1; // Force clear on first frame

    while (1) {
        // Chỉ clear màn hình khi đổi mode (tránh gửi 1KB I2C mỗi frame)
        if (data->mode != prev_mode) {
            ssd1306_clear(&dev);
            prev_mode = data->mode;
            vTaskDelay(pdMS_TO_TICKS(50)); // Nhả CPU sau khi clear
        }

        switch (data->mode) {
            case MODE_CONFIG:
                ssd1306_draw_string(&dev, 0, 1, "IoMT - PTIT");
                // ssd1306_draw_string(&dev, 0, 2, "Cho cau hinh    ");
                ssd1306_draw_string(&dev, 0, 3, "WiFi Configure ");
                ssd1306_draw_string(&dev, 0, 5, "SoftAP:");
                ssd1306_draw_string(&dev, 0, 7, "IoMT-PTIT");
                break;

            case MODE_IDLE: {
                // 1. Vẽ Logo bên trái (x=0, y=0, width=64, height=64)
                ssd1306_draw_bitmap(&dev, 0, 0, ptit_logo_64x64, 64, 64);

                // 2. Lấy giờ hiện tại (UTC+7)
                time_t now;
                struct tm timeinfo;
                time(&now);
                localtime_r(&now, &timeinfo);

                // 3. In Text bên phải (x=64, tối đa 8 ký tự/dòng)
                if (timeinfo.tm_year > (2020 - 1900)) {
                    // Cắt bớt năm: 24/03/26 (8 ký tự)
                    snprintf(buf, sizeof(buf), "%02d/%02d/%02d",
                             timeinfo.tm_mday, timeinfo.tm_mon + 1, (timeinfo.tm_year + 1900) % 100);
                    ssd1306_draw_string(&dev, 64, 1, buf);
                   
                    // Giờ: 22:55:40 (8 ký tự)
                    snprintf(buf, sizeof(buf), "%02d:%02d:%02d",
                             timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
                    ssd1306_draw_string(&dev, 64, 3, buf);
                } else {
                    ssd1306_draw_string(&dev, 64, 0, "Wait NTP");
                    ssd1306_draw_string(&dev, 64, 3, "        ");
                }
                vTaskDelay(pdMS_TO_TICKS(10)); // Nhả CPU giữa các dòng

                // ssd1306_draw_string(&dev, 64, 3, "IDLE    ");

                snprintf(buf, sizeof(buf), "T:%.1f C   ", data->room_temp);
                ssd1306_draw_string(&dev, 64, 5, buf);

                // ssd1306_draw_string(&dev, 64, 7, "Put hand");
                break;
            }

            case MODE_ACTIVE:
                ssd1306_draw_string(&dev, 0, 1, "HEALTH  MONITOR ");

                snprintf(buf, sizeof(buf), "BPM:%3d SpO2:%d%%", data->bpm, data->spo2);
                ssd1306_draw_string(&dev, 0, 3, buf);
                vTaskDelay(pdMS_TO_TICKS(10)); // Nhả CPU

                snprintf(buf, sizeof(buf), "Body: %.1f C    ", data->body_temp);
                ssd1306_draw_string(&dev, 0, 5, buf);

                snprintf(buf, sizeof(buf), "GSR: %-10d", data->gsr);
                ssd1306_draw_string(&dev, 0, 7, buf);

                // snprintf(buf, sizeof(buf), "Stress: %-8s",
                //          (data->stress > 0) ? "YES!" : "No");
                // ssd1306_draw_string(&dev, 0, 6, buf);
                break;
        }

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

// --- MONITOR TASK (MQTT interval thay đổi theo Mode) ---
void monitor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Monitor Task Started...");

    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    TickType_t last_mqtt_publish_time = 0;
    TickType_t last_serial_log_time = 0;

    while (1) {
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        TickType_t current_time = xTaskGetTickCount();

        // Thời gian chờ để log Serial: 1 phút (60s) ở IDLE, 5 giây ở ACTIVE/CONFIG
        TickType_t serial_interval = (data->mode == MODE_IDLE) ? pdMS_TO_TICKS(60000) : pdMS_TO_TICKS(5000);

        if (current_time - last_serial_log_time >= serial_interval || last_serial_log_time == 0) {
            // Serial log
            printf("Mode:%d,BPM:%d,SpO2:%d,GSR:%d,Stress:%d,RoomTemp:%.2f,BodyTemp:%.2f\n",
                   data->mode, data->bpm, data->spo2, data->gsr, data->stress,
                   data->room_temp, data->body_temp);
            last_serial_log_time = current_time;
        }

        // Kiểm tra xem đã đến lúc gửi MQTT chưa (ACTIVE: 1 phút, IDLE: 30 phút)
        TickType_t mqtt_interval = (data->mode == MODE_ACTIVE) ? pdMS_TO_TICKS(60000) : pdMS_TO_TICKS(1800000);

        if (current_time - last_mqtt_publish_time >= mqtt_interval || last_mqtt_publish_time == 0) {
            // Gửi MQTT
            char payload[256];
            snprintf(payload, sizeof(payload),
                     "{\"mode\": %d, \"room_temp\": %.1f, \"body_temp\": %.1f, \"bpm\": %d, \"spo2\": %d, \"gsr\": %d, \"stress\": %d}",
                     data->mode, data->room_temp, data->body_temp, data->bpm, data->spo2, data->gsr, data->stress);
            mqtt_manager_publish("ptit/health/data", payload);

            last_mqtt_publish_time = current_time;
        }

        // Delay ngắn gọn để cho phép task check các điều kiện liên tục mà không ăn 100% CPU
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

// --- APP MAIN ---
void app_main(void) {
    // 1. Khởi tạo NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Khởi tạo Health Data (Event Group + Struct)
    health_data_init();

    // 3. Khởi tạo WiFi Provisioning (sẽ tự gọi mqtt_manager_start khi có IP)
    ESP_LOGI(TAG, "Khoi dong trinh quan ly WiFi...");
    wifi_manager_init();

    // 4. Đồng bộ giờ qua SNTP (chờ WiFi xong mới sync được)
    sntp_init_time();

    // 5. Khởi tạo I2C bus
    sensor_hub_i2c_init();

    // 6. Tạo các FreeRTOS task
    xTaskCreate(sensor_hub_task, "sensor_hub", 8192, NULL, 5, NULL);
    xTaskCreate(gsr_sensor_task, "gsr_task", 4096, NULL, 5, NULL);
    xTaskCreate(ds18b20_task, "ds18b20_task", 4096, NULL, 5, NULL);
    xTaskCreate(monitor_task, "monitor_task", 4096, NULL, 4, NULL);
    xTaskCreate(display_task, "display_task", 4096, NULL, 4, NULL);
}
