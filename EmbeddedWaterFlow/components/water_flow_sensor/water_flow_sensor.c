#include "water_flow_sensor.h"
#include "yfs201_config.h"
#include "water_data.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/FreeRTOSConfig.h"
#include "freertos/task.h"

static const char *TAG = "YFS201";

static volatile uint32_t s_pulse_count_isr = 0;
static portMUX_TYPE s_pulse_mutex = portMUX_INITIALIZER_UNLOCKED;

static volatile bool s_new_pulse_event = false;
static portMUX_TYPE s_event_mutex = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR flow_pulse_isr(void *arg) {
    portENTER_CRITICAL_ISR(&s_pulse_mutex);
    s_pulse_count_isr++;
    portEXIT_CRITICAL_ISR(&s_pulse_mutex);

    portENTER_CRITICAL_ISR(&s_event_mutex);
    s_new_pulse_event = true;
    portEXIT_CRITICAL_ISR(&s_event_mutex);
}

static uint32_t get_and_reset_pulse_count(void) {
    uint32_t count;
    portENTER_CRITICAL(&s_pulse_mutex);
    count = s_pulse_count_isr;
    s_pulse_count_isr = 0;
    portEXIT_CRITICAL(&s_pulse_mutex);
    return count;
}

static float calculate_flow_rate(uint32_t pulses, uint32_t period_ms) {
    if (pulses == 0 || period_ms == 0) {
        return 0.0f;
    }
    return (float)pulses * 60000.0f / (YFS201_PULSES_PER_LITER * (float)period_ms);
}

static void update_flow_mode(water_sensor_data_t *data, float flow_rate) {
    static int active_cycles = 0;
    static int idle_cycles = 0;
    static int leak_cycles = 0;
    static int leak_cooldown = 0;

    if (flow_rate >= FLOW_DETECT_THRESHOLD) {
        idle_cycles = 0;
        active_cycles++;

        if (active_cycles >= FLOW_CONFIRM_CYCLES) {
            if (flow_rate < FLOW_LEAK_THRESHOLD) {
                data->mode = FLOW_MODE_LEAK;
                leak_cycles++;
                if (leak_cycles >= LEAK_ALERT_COOLDOWN_CYCLES && leak_cooldown <= 0) {
                    ESP_LOGW(TAG, "PHAT HIEN RO RI! Luu luong: %.2f L/min", flow_rate);
                    leak_cooldown = LEAK_ALERT_COOLDOWN_CYCLES;
                    leak_cycles = 0;
                }
                if (leak_cooldown > 0) leak_cooldown--;
            } else {
                data->mode = FLOW_MODE_ACTIVE;
                data->flow_detected = true;
                leak_cycles = 0;
                leak_cooldown = 0;
            }
        }
    } else {
        active_cycles = 0;
        idle_cycles++;
        leak_cycles = 0;

        if (idle_cycles >= FLOW_IDLE_CYCLES) {
            data->mode = FLOW_MODE_IDLE;
            data->flow_detected = false;
        }
    }
}

void water_flow_sensor_init(void) {
    ESP_LOGI(TAG, "Khoi tao YF-S201 tren GPIO %d...", YFS201_SIGNAL_PIN);

    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << YFS201_SIGNAL_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = YFS201_PULL_UP_ENABLED ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_POSEDGE,
    };
    gpio_config(&io_conf);

    gpio_install_isr_service(0);
    gpio_isr_handler_add(YFS201_SIGNAL_PIN, flow_pulse_isr, NULL);

    ESP_LOGI(TAG, "YF-S201 ready. VCC=5V, Signal=GPIO%d, GND=GND", YFS201_SIGNAL_PIN);
    ESP_LOGI(TAG, "Thong so: %d xung/L, chu ky tinh=%.1fs, nguong=%.2f L/min",
             (int)YFS201_PULSES_PER_LITER,
             FLOW_CALC_PERIOD_MS / 1000.0f,
             FLOW_DETECT_THRESHOLD);
}

void water_flow_sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Water Flow Sensor Task Started...");

    water_flow_sensor_init();

    water_sensor_data_t *data = water_data_get();
    EventGroupHandle_t evt = water_data_get_event_group();

    xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
    ESP_LOGI(TAG, "WiFi connected! YF-S201 sensor bat dau hoat dong.");

    uint32_t last_calc_time = 0;
    float prev_flow_rate = 0.0f;
    bool first_cycle = true;

    while (1) {
        uint32_t current_time = xTaskGetTickCount() * portTICK_PERIOD_MS;

        uint32_t elapsed = (current_time >= last_calc_time)
                           ? (current_time - last_calc_time)
                           : FLOW_CALC_PERIOD_MS;

        if (first_cycle || elapsed >= FLOW_CALC_PERIOD_MS) {
            uint32_t pulses = get_and_reset_pulse_count();
            uint32_t period_ms = first_cycle ? FLOW_CALC_PERIOD_MS : elapsed;

            float flow_rate = calculate_flow_rate(pulses, period_ms);

            data->pulse_count += pulses;
            float volume_this_cycle = (flow_rate * period_ms) / 60000.0f;
            data->total_volume += volume_this_cycle;
            data->flow_rate = flow_rate;

            update_flow_mode(data, flow_rate);

            if (flow_rate != prev_flow_rate || data->mode != FLOW_MODE_IDLE) {
                ESP_LOGI(TAG, "Flow: %.2f L/min | Total: %.3f L | Pulses: %lu | Mode: %d",
                         flow_rate, data->total_volume, pulses, data->mode);
                prev_flow_rate = flow_rate;
            }

            last_calc_time = current_time;
            first_cycle = false;
        }

        vTaskDelay(pdMS_TO_TICKS(FLOW_CALC_PERIOD_MS));
    }
}
