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
#include "ds18b20_sensor.h"
#include "ds18b20_config.h"
#include "thermal_processor.h"
#include "dht11_sensor.h"
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
    ds18b20_sensor_init(DS18B20_PIN);

    thermal_processor_t tp;
    thermal_processor_init(&tp);

    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    while (1) {
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        float raw_temp = ds18b20_sensor_get_temp();
        if (raw_temp > -100.0f) {
            thermal_processor_update(&tp, raw_temp, data->is_user_present,
                                     data->ambient_temp, data->humidity);

            data->room_temp = thermal_processor_get_room_temp(&tp);

            float new_body = thermal_processor_get_body_temp(&tp);
            if (new_body > 0.0f) {
                data->body_temp = new_body;
            } else if (!data->is_user_present) {
                data->body_temp = 0.0f;
            }

            data->measurement_confidence = thermal_processor_get_confidence(&tp);
            data->dht11_bias = thermal_processor_get_bias(&tp);
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
        if (data->mode != prev_mode) {
            ssd1306_clear(&dev);
            prev_mode = data->mode;
            vTaskDelay(pdMS_TO_TICKS(50));
        }

        switch (data->mode) {
            case MODE_CONFIG:
                ssd1306_draw_string(&dev, 0, 1, "IoMT - PTIT");
                ssd1306_draw_string(&dev, 0, 3, "WiFi Configure ");
                ssd1306_draw_string(&dev, 0, 5, "SoftAP:");
                ssd1306_draw_string(&dev, 0, 7, "IoMT-PTIT");
                break;

            case MODE_IDLE: {
                ssd1306_draw_bitmap(&dev, 0, 0, ptit_logo_64x64, 64, 64);

                time_t now;
                struct tm timeinfo;
                time(&now);
                localtime_r(&now, &timeinfo);

                if (timeinfo.tm_year > (2020 - 1900)) {
                    ssd1306_draw_string(&dev, 64, 0, "        ");
                    snprintf(buf, sizeof(buf), "%02d/%02d/%02d",
                             timeinfo.tm_mday, timeinfo.tm_mon + 1, (timeinfo.tm_year + 1900) % 100);
                    ssd1306_draw_string(&dev, 64, 1, buf);

                    snprintf(buf, sizeof(buf), "%02d:%02d:%02d",
                             timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
                    ssd1306_draw_string(&dev, 64, 3, buf);
                } else {
                    ssd1306_draw_string(&dev, 64, 1, "Wait NTP");
                    ssd1306_draw_string(&dev, 64, 3, "        ");
                }
                vTaskDelay(pdMS_TO_TICKS(10));

                snprintf(buf, sizeof(buf), "A:%.1f C   ", data->ambient_temp);
                ssd1306_draw_string(&dev, 64, 5, buf);

                snprintf(buf, sizeof(buf), "H:%3d%%    ", data->humidity);
                ssd1306_draw_string(&dev, 64, 6, buf);
                break;
            }

            case MODE_CALIBRATE: {
                ssd1306_draw_string(&dev, 0, 0, "GSR CALIBRATION  ");
                ssd1306_draw_string(&dev, 0, 2, "Adjust to 2200   ");

                if (data->gsr_raw > 0) {
                    snprintf(buf, sizeof(buf), "Raw: %-5d     ", data->gsr_raw);
                } else {
                    snprintf(buf, sizeof(buf), "Raw: ----       ");
                }
                ssd1306_draw_string(&dev, 0, 4, buf);

                if (data->calibrate_done) {
                    snprintf(buf, sizeof(buf), "GSR: %-5d     ", data->gsr);
                    ssd1306_draw_string(&dev, 0, 5, buf);
                    snprintf(buf, sizeof(buf), "Offset: %-5d   ", data->gsr_offset);
                    ssd1306_draw_string(&dev, 0, 6, buf);
                } else {
                    ssd1306_draw_string(&dev, 0, 5, "GSR: --        ");
                    ssd1306_draw_string(&dev, 0, 6, "Hold btn to save");
                }

                ssd1306_draw_string(&dev, 0, 7, "Target: 2200    ");
                break;
            }

            case MODE_ACTIVE:
                ssd1306_draw_string(&dev, 0, 1, "HEALTH  MONITOR ");

                if (data->bpm > 0) {
                    snprintf(buf, sizeof(buf), "BPM:%3d SpO2:%d%%", data->bpm, data->spo2);
                } else {
                    snprintf(buf, sizeof(buf), "BPM:--- SpO2:--%%");
                }
                ssd1306_draw_string(&dev, 0, 3, buf);
                vTaskDelay(pdMS_TO_TICKS(10));

                if (data->room_temp > 0 && data->body_temp > 30.0f) {
                    snprintf(buf, sizeof(buf), "Body: %.1f C    ", data->body_temp);
                } else {
                    snprintf(buf, sizeof(buf), "Body: --.- C    ");
                }
                ssd1306_draw_string(&dev, 0, 5, buf);

                snprintf(buf, sizeof(buf), "H:%3d%%  GSR:%4d", data->humidity, data->gsr);
                ssd1306_draw_string(&dev, 0, 6, buf);

                if (data->calibrate_done) {
                    snprintf(buf, sizeof(buf), "OFFSET:%-5d   ", data->gsr_offset);
                } else {
                    snprintf(buf, sizeof(buf), "NOT CALIBRATED ");
                }
                ssd1306_draw_string(&dev, 0, 7, buf);
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

        TickType_t serial_interval = (data->mode == MODE_IDLE) ? pdMS_TO_TICKS(60000) : pdMS_TO_TICKS(100);

        if (current_time - last_serial_log_time >= serial_interval || last_serial_log_time == 0) {
            int pub_bpm = (data->bpm > 0) ? data->bpm : 0;
            int pub_spo2 = (data->bpm > 0) ? data->spo2 : 0;
            int pub_gsr = (data->gsr < 4000) ? data->gsr : 0;
            float pub_body = data->body_temp;

            if (data->mode == MODE_IDLE) {
                printf("Mode:%d,AmbientDHT:%.2f,RoomDS:%.2f,Bias:%.3f\n",
                       data->mode, data->ambient_temp, data->room_temp,
                       data->dht11_bias);
            } else {
                printf("Mode:%d,BPM:%d,SpO2:%d,GSR:%d,Ambient:%.2f,BodyTemp:%.2f,Conf:%d,CalOffset:%d\n",
                       data->mode, pub_bpm, pub_spo2, pub_gsr,
                       data->ambient_temp, pub_body, data->measurement_confidence,
                       data->gsr_offset);
            }
            last_serial_log_time = current_time;
        }

        if (data->mode != MODE_IDLE) {
            TickType_t mqtt_interval = (data->mode == MODE_ACTIVE) ? pdMS_TO_TICKS(1000) : pdMS_TO_TICKS(60000);

            if (current_time - last_mqtt_publish_time >= mqtt_interval || last_mqtt_publish_time == 0) {
                int pub_bpm = (data->bpm > 0) ? data->bpm : 0;
                int pub_spo2 = (data->bpm > 0) ? data->spo2 : 0;
                int pub_gsr = (data->gsr < 4000) ? data->gsr : 0;
                float pub_body = data->body_temp;

                time_t now;
                struct tm timeinfo;
                time(&now);
                localtime_r(&now, &timeinfo);
                char time_str[64];
                snprintf(time_str, sizeof(time_str), "%04d:%02d:%02d - %02d:%02d:%02d",
                         timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                         timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);

                char payload[512];
                snprintf(payload, sizeof(payload),
                         "{\"timestamp\": \"%s\", \"mode\": %d, \"dht11_room_temp\": %.1f, \"dht11_humidity\": %d, "
                         "\"body_temp\": %.1f, \"bpm\": %d, \"spo2\": %d, \"gsr\": %d, "
                         "\"confidence\": %d, \"dht11_bias\": %.3f}",
                         time_str, data->mode, data->ambient_temp, data->humidity,
                         pub_body, pub_bpm, pub_spo2, pub_gsr,
                         data->measurement_confidence, data->dht11_bias);

                mqtt_manager_publish("ptit/health/data", payload);

                last_mqtt_publish_time = current_time;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(50));
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

    // 3. Khởi tạo WiFi Provisioning
    ESP_LOGI(TAG, "Khoi dong trinh quan ly WiFi...");
    wifi_manager_init();

    // 4. Đồng bộ giờ qua SNTP
    sntp_init_time();

    // 5. Khởi tạo I2C bus
    sensor_hub_i2c_init();

    // 6. Tạo các FreeRTOS task
    xTaskCreate(sensor_hub_task, "sensor_hub", 8192, NULL, 5, NULL);
    xTaskCreate(gsr_sensor_task, "gsr_task", 4096, NULL, 3, NULL);
    xTaskCreate(ds18b20_task, "ds18b20_task", 4096, NULL, 3, NULL);
    xTaskCreate(dht11_sensor_task, "dht11_task", 4096, NULL, 3, NULL);
    xTaskCreate(monitor_task, "monitor_task", 8192, NULL, 4, NULL);
    xTaskCreate(display_task, "display_task", 4096, NULL, 3, NULL);
}
