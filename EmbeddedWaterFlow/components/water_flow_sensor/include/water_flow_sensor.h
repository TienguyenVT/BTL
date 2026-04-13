#pragma once

#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

void water_flow_sensor_task(void *pvParameters);
void water_flow_sensor_init(void);
