#pragma once

#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

#define WIFI_CONNECTED_BIT BIT0
#define WATER_WIFI_AP_SSID "WaterFlow-Setup"
#define WATER_WIFI_AP_PASSWORD ""
#define HTTP_PORT 80

void wifi_manager_init(void);
void wifi_manager_reset(void);
bool wifi_manager_is_configured(void);
void wifi_manager_clear_config(void);