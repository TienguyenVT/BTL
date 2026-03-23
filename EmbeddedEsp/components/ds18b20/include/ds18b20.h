#pragma once
#include "driver/gpio.h"

void ds18b20_init(gpio_num_t pin);
float ds18b20_get_temp(void);
