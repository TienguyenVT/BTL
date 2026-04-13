#pragma once

#include "driver/gpio.h"

#define YFS201_SIGNAL_PIN          GPIO_NUM_4

#define YFS201_PULL_UP_ENABLED     1

#define YFS201_PULSES_PER_LITER    450.0f


#define FLOW_CALC_PERIOD_MS        1000


#define FLOW_DETECT_THRESHOLD      0.1f

#define FLOW_LEAK_THRESHOLD        2.0f

#define FLOW_CONFIRM_CYCLES        3

#define FLOW_IDLE_CYCLES           5

#define LEAK_ALERT_COOLDOWN_CYCLES 60
