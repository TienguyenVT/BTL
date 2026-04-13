#include "water_data.h"
#include <stdlib.h>

static water_sensor_data_t s_water_data = {
    .flow_rate = 0.0f,
    .total_volume = 0.0f,
    .pulse_count = 0,
    .flow_detected = false,
    .mode = FLOW_MODE_IDLE,
    .voltage = 0.0f,
    .current = 0.0f,
    .power = 0.0f,
    .total_energy_wh = 0.0f,
    .total_energy_kwh = 0.0f,
    .last_energy_tick = 0,
};

static EventGroupHandle_t s_wifi_event_group = NULL;

water_sensor_data_t *water_data_get(void) {
    return &s_water_data;
}

EventGroupHandle_t water_data_get_event_group(void) {
    return s_wifi_event_group;
}

void water_data_init(void) {
    s_wifi_event_group = xEventGroupCreate();
}

void water_data_update_energy(uint32_t current_tick_ms) {
    if (s_water_data.last_energy_tick == 0) {
        s_water_data.last_energy_tick = current_tick_ms;
        return;
    }

    uint32_t delta_ms = current_tick_ms - s_water_data.last_energy_tick;
    if (delta_ms == 0 || delta_ms > 60000) {
        s_water_data.last_energy_tick = current_tick_ms;
        return;
    }

    float delta_hours = delta_ms / 3600000.0f;
    float power_kw = s_water_data.power / 1000.0f;
    float energy_delta_kwh = power_kw * delta_hours;
    float energy_delta_wh = power_kw * delta_hours * 1000.0f;

    s_water_data.total_energy_kwh += energy_delta_kwh;
    s_water_data.total_energy_wh += energy_delta_wh;
    s_water_data.last_energy_tick = current_tick_ms;
}
