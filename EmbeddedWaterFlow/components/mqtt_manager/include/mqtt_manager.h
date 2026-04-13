#pragma once

#include <stdbool.h>
#include "driver/gpio.h"

void mqtt_manager_init_relay(gpio_num_t relay_gpio);
void mqtt_manager_start(void);
void mqtt_manager_publish_sensor_data(const char *json_payload);
void mqtt_manager_set_relay(bool state);
bool mqtt_manager_get_relay_state(void);
bool mqtt_manager_is_connected(void);
