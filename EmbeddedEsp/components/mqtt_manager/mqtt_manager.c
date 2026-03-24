#include "mqtt_manager.h"
#include "mqtt_client.h"
#include "esp_crt_bundle.h"
#include "esp_log.h"
#include <stdbool.h>

static const char *TAG = "MQTT";

static esp_mqtt_client_handle_t s_mqtt_client = NULL;
static bool s_mqtt_connected = false;

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = event_data;
    switch ((esp_mqtt_event_id_t)event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "Da ket noi HiveMQ Cloud");
            s_mqtt_connected = true;
            break;
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "Mat ket noi HiveMQ Cloud");
            s_mqtt_connected = false;
            break;
        case MQTT_EVENT_PUBLISHED:
            ESP_LOGD(TAG, "Gui thanh cong msg_id=%d", event->msg_id);
            break;
        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "Loi doc / ghi MQTT!");
            break;
        default:
            break;
    }
}

void mqtt_manager_start(void) {
    if (s_mqtt_client != NULL) {
        return; // Đã khởi tạo rồi
    }

    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtts://6b09ec30252741efa972f3f845ce726d.s1.eu.hivemq.cloud:8883",
        .credentials.username = "Ptit1234",
        .credentials.authentication.password = "Ptit1234",
        .broker.verification.crt_bundle_attach = esp_crt_bundle_attach,
    };
    s_mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(s_mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(s_mqtt_client);
}

void mqtt_manager_publish(const char *topic, const char *payload) {
    if (s_mqtt_client != NULL && s_mqtt_connected) {
        int msg_id = esp_mqtt_client_publish(s_mqtt_client, topic, payload, 0, 0, 0);
        if (msg_id != -1) {
            ESP_LOGI(TAG, "MQTT Pub: %s", payload);
        }
    }
}

bool mqtt_manager_is_connected(void) {
    return s_mqtt_connected;
}
