#include "health_data.h"

static health_data_t s_health_data = {
    .bpm = 0,
    .spo2 = 0,
    .gsr = 0,
    .gsr_raw = 0,
    .gsr_baseline = 2200,
    .gsr_offset = 0,
    .body_temp = 0.0f,
    .room_temp = 0.0f,
    .humidity = 0,
    .ambient_temp = 25.0f,
    .dht11_temperature = 0.0f,
    .dht11_bias = 0.0f,
    .measurement_confidence = 0,
    .measurement_quality = MEAS_QUALITY_INVALID,
    .mode = MODE_CONFIG,
    .is_user_present = false,
    .temp_baseline = 0.0f,
    .calibrate_active = false,
    .calibrate_done = false,
};

static EventGroupHandle_t s_wifi_event_group = NULL;

health_data_t *health_data_get(void) {
    return &s_health_data;
}

EventGroupHandle_t health_data_get_event_group(void) {
    return s_wifi_event_group;
}

void health_data_init(void) {
    s_wifi_event_group = xEventGroupCreate();
}
