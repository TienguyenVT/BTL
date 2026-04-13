#include "pzem004t.h"
#include "pzem004t_config.h"
#include "water_data.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include <string.h>
#include <unistd.h>

static const char *TAG = "PZEM004T";

static int s_uart_port = -1;

#define PZEM_CMD_LEN       8
#define PZEM_RESPONSE_LEN  25
#define PZEM_BUFFER_SIZE   256

static uint16_t calc_crc16(const uint8_t *data, uint8_t len) {
    uint16_t crc = 0xFFFF;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x0001) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

static esp_err_t send_read_command(void) {
    uint8_t cmd[PZEM_CMD_LEN] = {
        PZEM_DEFAULT_ADDR, 
        0x04,              
        0x00,            
        0x00,              
        0x00,            
        0x0A,               
        0x00,             
        0x00                
    };


    uint16_t crc = calc_crc16(cmd, 6);
    cmd[6] = crc & 0xFF;         
    cmd[7] = (crc >> 8) & 0xFF;

    int len = uart_write_bytes(s_uart_port, (const char *)cmd, PZEM_CMD_LEN);
    if (len != PZEM_CMD_LEN) {
        ESP_LOGE(TAG, "UART write error: %d bytes sent", len);
        return ESP_FAIL;
    }

    return ESP_OK;
}

static esp_err_t read_response(float *voltage, float *current, float *power) {
    uint8_t buffer[PZEM_BUFFER_SIZE];

    int len = uart_read_bytes(s_uart_port, buffer, PZEM_RESPONSE_LEN,
                              pdMS_TO_TICKS(PZEM_UART_TIMEOUT_MS));

    if (len < 0) {
        ESP_LOGE(TAG, "UART read error");
        return ESP_FAIL;
    }

    if (len < PZEM_RESPONSE_LEN) {
        ESP_LOGW(TAG, "Incomplete response: %d bytes (expected %d)", len, PZEM_RESPONSE_LEN);
        uart_flush_input(s_uart_port);
        return ESP_ERR_INVALID_SIZE;
    }

    if (buffer[0] != PZEM_DEFAULT_ADDR) {
        ESP_LOGW(TAG, "Wrong slave address: 0x%02X", buffer[0]);
        return ESP_ERR_INVALID_RESPONSE;
    }

    if (buffer[1] != 0x04) {
        ESP_LOGW(TAG, "Wrong function code: 0x%02X", buffer[1]);
        return ESP_ERR_INVALID_RESPONSE;
    }

    if (buffer[2] != 20) {
        ESP_LOGW(TAG, "Wrong byte count: %d", buffer[2]);
        return ESP_ERR_INVALID_RESPONSE;
    }

    uint16_t recv_crc = buffer[23] | (buffer[24] << 8);
    uint16_t calc_crc = calc_crc16(buffer, 23);
    if (recv_crc != calc_crc) {
        ESP_LOGE(TAG, "CRC error: received=0x%04X, calculated=0x%04X", recv_crc, calc_crc);
        return ESP_ERR_INVALID_CRC;
    }

    uint16_t voltage_reg = (buffer[3] << 8) | buffer[4];
    *voltage = voltage_reg * 0.1f;

    uint32_t current_reg = (((uint32_t)buffer[7] << 8) | buffer[8]) << 16 |
                           (((uint32_t)buffer[5] << 8) | buffer[6]);
    *current = current_reg * 0.001f;

    uint32_t power_reg = (((uint32_t)buffer[11] << 8) | buffer[12]) << 16 |
                         (((uint32_t)buffer[9] << 8) | buffer[10]);
    *power = power_reg * 0.1f;

    return ESP_OK;
}

static esp_err_t uart_init_(void) {
    uart_config_t uart_config = {
        .baud_rate = PZEM_BAUD_RATE,
        .data_bits = PZEM_DATA_BITS,
        .parity = PZEM_PARITY,
        .stop_bits = PZEM_STOP_BITS,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };

    int intr_flags = 0;

    ESP_LOGI(TAG, "UART config: port=%d, baud=%d, TX=%d, RX=%d",
             PZEM_UART_NUM, PZEM_BAUD_RATE, PZEM_TX_PIN, PZEM_RX_PIN);

    esp_err_t err = uart_param_config(PZEM_UART_NUM, &uart_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "UART param config failed: %s", esp_err_to_name(err));
        return err;
    }

    err = uart_set_pin(PZEM_UART_NUM, PZEM_TX_PIN, PZEM_RX_PIN,
                       UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "UART set pin failed: %s", esp_err_to_name(err));
        return err;
    }

    err = uart_driver_install(PZEM_UART_NUM, PZEM_BUFFER_SIZE,
                              PZEM_BUFFER_SIZE, 0, NULL, intr_flags);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed: %s", esp_err_to_name(err));
        return err;
    }

    s_uart_port = PZEM_UART_NUM;
    ESP_LOGI(TAG, "UART init done on port %d", s_uart_port);
    return ESP_OK;
}

void pzem004t_init(void) {
    ESP_LOGI(TAG, "Initializing PZEM-004T...");

    esp_err_t err = uart_init_();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "UART init failed!");
        return;
    }

    ESP_LOGI(TAG, "PZEM-004T ready. UART2, TX=GPIO%d, RX=GPIO%d, Baud=%d",
             PZEM_TX_PIN, PZEM_RX_PIN, PZEM_BAUD_RATE);
    ESP_LOGI(TAG, "Measuring: Voltage, Current, Power");
}

void pzem004t_task(void *pvParameters) {
    ESP_LOGI(TAG, "PZEM-004T Task Started...");

    EventGroupHandle_t evt = water_data_get_event_group();
    xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
    ESP_LOGI(TAG, "WiFi connected! PZEM-004T bat dau hoat dong.");

    pzem004t_init();

    water_sensor_data_t *data = water_data_get();

    int retry_count = 0;

    while (1) {
        esp_err_t err = send_read_command();
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Failed to send command, retrying...");
            retry_count++;
            vTaskDelay(pdMS_TO_TICKS(500));
            if (retry_count >= PZEM_MAX_RETRIES) {
                ESP_LOGE(TAG, "Max retries reached, skipping cycle");
                retry_count = 0;
                vTaskDelay(pdMS_TO_TICKS(PZEM_READ_INTERVAL_MS));
            }
            continue;
        }

        float voltage = 0.0f;
        float current = 0.0f;
        float power = 0.0f;

        err = read_response(&voltage, &current, &power);
        if (err == ESP_OK) {
            retry_count = 0;

            data->voltage = voltage;
            data->current = current;
            data->power = power;

            water_data_update_energy(esp_timer_get_time() / 1000);
        } else {
            retry_count++;
            ESP_LOGW(TAG, "Read failed (retry %d/%d): %s",
                     retry_count, PZEM_MAX_RETRIES, esp_err_to_name(err));

            if (retry_count >= PZEM_MAX_RETRIES) {
                ESP_LOGE(TAG, "Max retries reached");
                retry_count = 0;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(PZEM_READ_INTERVAL_MS));
    }
}
