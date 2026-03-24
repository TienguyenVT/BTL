#pragma once

#include <driver/i2c.h>
#include <stdbool.h>
#include <stdint.h>
#include "max30105_config.h"

typedef struct {
  i2c_port_t i2c_port;
  uint8_t i2c_address;
} max30105_t;

// Initialization
bool max30105_begin(max30105_t *sensor, i2c_port_t port, uint32_t speed);

// Configuration
void max30105_setup(max30105_t *sensor, uint8_t powerLevel,
                    uint8_t sampleAverage, uint8_t ledMode, int sampleRate,
                    int pulseWidth, int adcRange);

// Data Retrieval
uint32_t max30105_getRed(void);
uint32_t max30105_getIR(void);
uint32_t max30105_getGreen(void);
bool max30105_available(void);
void max30105_check(max30105_t *sensor);
void max30105_nextSample(void);

// Low-level register access (if needed)
uint8_t max30105_readRegister8(max30105_t *sensor, uint8_t reg);
void max30105_writeRegister8(max30105_t *sensor, uint8_t reg, uint8_t value);
