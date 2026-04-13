#include "relay_control.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "RELAY";

static gpio_num_t s_relay_gpio = RELAY_GPIO_PIN;
static bool s_relay_on = false;

void relay_init(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << s_relay_gpio),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

    relay_off();
    ESP_LOGI(TAG, "Relay initialized on GPIO %d (default: OFF)", s_relay_gpio);
}

void relay_on(void) {
    gpio_set_level(s_relay_gpio, 0);
    s_relay_on = true;
    ESP_LOGI(TAG, "Relay ON");
}

void relay_off(void) {
    gpio_set_level(s_relay_gpio, 1);
    s_relay_on = false;
    ESP_LOGI(TAG, "Relay OFF");
}

void relay_toggle(void) {
    if (s_relay_on) {
        relay_off();
    } else {
        relay_on();
    }
}

bool relay_get_state(void) {
    return s_relay_on;
}
