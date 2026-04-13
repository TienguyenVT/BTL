#include "esp_log.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>

#include "water_data.h"
#include "wifi_manager.h"
#include "water_flow_sensor.h"
#include "pzem004t.h"
#include "mqtt_manager.h"
#include "relay_control.h"

static const char *TAG = "MAIN";

static const char *mode_to_string(flow_mode_t mode) {
    switch (mode) {
        case FLOW_MODE_CONFIG: return "CONFIG";
        case FLOW_MODE_IDLE:   return "IDLE";
        case FLOW_MODE_ACTIVE: return "ACTIVE";
        case FLOW_MODE_LEAK:   return "LEAK";
        default:               return "UNKNOWN";
    }
}

void monitor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Monitor Task Started...");

    water_sensor_data_t *data = water_data_get();
    EventGroupHandle_t evt = water_data_get_event_group();

    TickType_t last_serial_time = 0;
    TickType_t last_mqtt_time = 0;

    while (1) {
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        TickType_t current_time = xTaskGetTickCount();

        TickType_t serial_interval;
        if (data->mode == FLOW_MODE_CONFIG) {
            serial_interval = pdMS_TO_TICKS(5000);
        } else if (data->mode == FLOW_MODE_IDLE) {
            serial_interval = pdMS_TO_TICKS(10000);
        } else {
            serial_interval = pdMS_TO_TICKS(2000);
        }

        if (current_time - last_serial_time >= serial_interval || last_serial_time == 0) {
            printf("\n========== Water Flow Monitor ==========\n");
            printf("  Mode:    %s\n", mode_to_string(data->mode));
            printf("  MAC:     %s\n", data->mac_address);

            if (data->mode == FLOW_MODE_CONFIG) {
                printf("  Status:  Phat SoftAP 'WaterFlow-Setup'\n");
                printf("  IP:      192.168.4.1\n");
                printf("  Pass:    12345678\n");
            } else {
                printf("  --- YF-S201 ---\n");
                printf("  Flow:    %.2f L/min\n", data->flow_rate);
                printf("  Total:   %.3f L\n", data->total_volume);
                printf("  Pulses:  %lu\n", data->pulse_count);
                printf("  --- PZEM-004T ---\n");
                printf("  Voltage: %.1f V\n", data->voltage);
                printf("  Current: %.3f A\n", data->current);
                printf("  Power:   %.1f W\n", data->power);
                printf("  Energy:  %.4f kWh\n", data->total_energy_kwh);
                printf("  --- Relay ---\n");
                printf("  State:   %s\n", relay_get_state() ? "ON" : "OFF");
            }
            printf("==========================================\n");
            last_serial_time = current_time;
        }

        if (current_time - last_mqtt_time >= pdMS_TO_TICKS(1000) || last_mqtt_time == 0) {
            if (data->mode != FLOW_MODE_CONFIG) {
                time_t now = time(NULL);
                struct tm timeinfo;
                localtime_r(&now, &timeinfo);
                char time_str[32];
                strftime(time_str, sizeof(time_str), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);

                char payload[512];
                snprintf(payload, sizeof(payload),
                    "{\"timestamp\":\"%s\",\"mac_address\":\"%s\","
                    "\"voltage\":%.1f,\"current\":%.3f,\"power\":%.1f,\"energy\":%.4f,"
                    "\"flow_rate\":%.2f,\"total_volume\":%.3f,\"pulse_count\":%lu,\"mode\":\"%s\"}",
                    time_str, data->mac_address,
                    data->voltage, data->current, data->power, data->total_energy_kwh,
                    data->flow_rate, data->total_volume, data->pulse_count,
                    mode_to_string(data->mode));

                mqtt_manager_publish_sensor_data(payload);
            }
            last_mqtt_time += pdMS_TO_TICKS(1000);
        }

        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "==========================================");
    ESP_LOGI(TAG, "  Water Flow Sensor - YF-S201 + PZEM-004T");
    ESP_LOGI(TAG, "  ESP32 WiFi Config via Web Portal");
    ESP_LOGI(TAG, "  MQTT: HiveMQ Cloud");
    ESP_LOGI(TAG, "==========================================");

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    water_data_init();

    ESP_LOGI(TAG, "Khoi dong WiFi Provisioning...");
    wifi_manager_init();

    water_flow_sensor_init();
    pzem004t_init();

    xTaskCreate(water_flow_sensor_task, "water_flow_task", 4096, NULL, 5, NULL);
    xTaskCreate(pzem004t_task,          "pzem_task",       4096, NULL, 5, NULL);
    xTaskCreate(monitor_task,          "monitor_task",    4096, NULL, 3, NULL);

    ESP_LOGI(TAG, "System started. Mo trinh duyet vao 192.168.4.1 de cau hinh WiFi!");
}
