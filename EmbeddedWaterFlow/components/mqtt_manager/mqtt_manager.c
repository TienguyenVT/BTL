#include "mqtt_manager.h"
#include "mqtt_config.h"
#include "relay_control.h"
#include "water_data.h"
#include "mqtt_client.h"
#include "esp_crt_bundle.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include <stdbool.h>
#include <string.h>
#include <stdio.h>

static const char *TAG = "MQTT";

static esp_mqtt_client_handle_t s_mqtt_client = NULL;
static bool s_mqtt_connected = false;
static bool s_relay_initialized = false;

static void mqtt_manager_publish_relay_status_(void);

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "Da ket noi HiveMQ Cloud");
            s_mqtt_connected = true;

            if (s_mqtt_client != NULL) {
                int sub_id = esp_mqtt_client_subscribe(s_mqtt_client, MQTT_RELAY_SUB_TOPIC, 1);
                ESP_LOGI(TAG, "Subscribed to '%s' (msg_id=%d)", MQTT_RELAY_SUB_TOPIC, sub_id);
            }
            break;

        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "Mat ket noi HiveMQ Cloud");
            s_mqtt_connected = false;
            break;

        case MQTT_EVENT_SUBSCRIBED:
            ESP_LOGI(TAG, "Subscribe thanh cong, msg_id=%d", event->msg_id);
            break;

        case MQTT_EVENT_PUBLISHED:
            ESP_LOGI(TAG, "Gui thanh cong, msg_id=%d", event->msg_id);
            break;

        case MQTT_EVENT_DATA:
            ESP_LOGI(TAG, "Nhan du lieu MQTT: topic='%.*s'", event->topic_len, event->topic);

            if (strncmp(event->topic, MQTT_RELAY_SUB_TOPIC, strlen(MQTT_RELAY_SUB_TOPIC)) == 0) {
                char cmd[32] = {0};
                int data_len = event->data_len;
                if (data_len >= (int)sizeof(cmd)) {
                    data_len = sizeof(cmd) - 1;
                }
                memcpy(cmd, event->data, data_len);
                cmd[data_len] = '\0';

                ESP_LOGI(TAG, "Relay command: %s", cmd);

                if (strstr(cmd, "\"relay\":\"ON\"") || strstr(cmd, "\"relay\":\"on\"")) {
                    relay_on();
                    mqtt_manager_publish_relay_status_();
                } else if (strstr(cmd, "\"relay\":\"OFF\"") || strstr(cmd, "\"relay\":\"off\"")) {
                    relay_off();
                    mqtt_manager_publish_relay_status_();
                } else if (strstr(cmd, "\"relay\":\"TOGGLE\"") || strstr(cmd, "\"relay\":\"toggle\"")) {
                    relay_toggle();
                    mqtt_manager_publish_relay_status_();
                }
            }
            break;

        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "Loi MQTT!");
            break;

        default:
            break;
    }
}

void mqtt_manager_init_relay(gpio_num_t relay_gpio) {
    (void)relay_gpio;
    relay_init();
    s_relay_initialized = true;
    ESP_LOGI(TAG, "Relay da san sang");
}

void mqtt_manager_start(void) {
    if (s_mqtt_client != NULL) {
        return;
    }

    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = MQTT_BROKER_URI,
        .credentials.username = MQTT_USERNAME,
        .credentials.authentication.password = MQTT_PASSWORD,
        .broker.verification.crt_bundle_attach = esp_crt_bundle_attach,
        .network.timeout_ms = MQTT_TIMEOUT_MS,
        .task.priority = 5,
        .task.stack_size = 8192,
    };

    s_mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(s_mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(s_mqtt_client);

    ESP_LOGI(TAG, "MQTT client da khoi dong");
}

void mqtt_manager_publish_sensor_data(const char *json_payload) {
    if (s_mqtt_client != NULL && s_mqtt_connected) {
        int msg_id = esp_mqtt_client_publish(s_mqtt_client, MQTT_PUB_TOPIC, json_payload, 0, 0, 0);
        if (msg_id != -1) {
        ESP_LOGI(TAG, "Pub sensor data: %s", json_payload);
        }
    }
}

static void mqtt_manager_publish_relay_status_(void) {
    if (s_mqtt_client == NULL || !s_mqtt_connected) {
        return;
    }

    water_sensor_data_t *data = water_data_get();
    char payload[128];
    snprintf(payload, sizeof(payload),
             "{\"relay\":\"%s\",\"mac_address\":\"%s\"}",
             relay_get_state() ? "ON" : "OFF",
             data->mac_address);

    int msg_id = esp_mqtt_client_publish(s_mqtt_client, MQTT_RELAY_PUB_TOPIC, payload, 0, 0, 0);
    if (msg_id != -1) {
        ESP_LOGI(TAG, "Pub relay status: %s", payload);
    }
}

void mqtt_manager_set_relay(bool state) {
    if (state) {
        relay_on();
    } else {
        relay_off();
    }
    mqtt_manager_publish_relay_status_();
}

bool mqtt_manager_get_relay_state(void) {
    return relay_get_state();
}

bool mqtt_manager_is_connected(void) {
    return s_mqtt_connected;
}
