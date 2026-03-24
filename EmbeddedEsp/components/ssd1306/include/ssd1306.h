#ifndef __SSD1306_H__
#define __SSD1306_H__

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#define SSD1306_I2C_ADDRESS 0x3C

typedef struct {
    i2c_port_t i2c_port;
    uint8_t address;
} ssd1306_t;

void ssd1306_init(ssd1306_t *dev, i2c_port_t i2c_port);
void ssd1306_clear(ssd1306_t *dev);
void ssd1306_draw_string(ssd1306_t *dev, uint8_t x, uint8_t page, const char *str);
void ssd1306_display_on(ssd1306_t *dev);
void ssd1306_display_off(ssd1306_t *dev);

#endif // __SSD1306_H__
