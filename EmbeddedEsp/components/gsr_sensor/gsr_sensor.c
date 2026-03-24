#include "gsr_sensor.h"
#include "health_data.h"
#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "GSR";

void gsr_sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "GSR Sensor Task Started...");

    // Khởi tạo ADC oneshot
    adc_oneshot_unit_handle_t adc1_handle;
    adc_oneshot_unit_init_cfg_t init_config1 = {
        .unit_id = GSR_ADC_UNIT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config1, &adc1_handle));

    // Cấu hình kênh ADC
    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc1_handle, GSR_ADC_CHANNEL, &config));

    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    while (1) {
        // Chờ WiFi kết nối
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        long sum = 0;

        // Thuật toán lọc nhiễu (Averaging Filter)
        for (int i = 0; i < GSR_SAMPLE_SIZE; i++) {
            int analog_val;
            ESP_ERROR_CHECK(adc_oneshot_read(adc1_handle, GSR_ADC_CHANNEL, &analog_val));
            sum += analog_val;
            vTaskDelay(pdMS_TO_TICKS(2));
        }

        int gsr_average = sum / GSR_SAMPLE_SIZE;

        // Phát hiện Stress
        int stress_detect = 0;
        if (gsr_average > (GSR_BASELINE + GSR_THRESHOLD_STRESS)) {
            stress_detect = 4000;
        }

        // Cập nhật dữ liệu toàn cục
        data->gsr = gsr_average;
        data->stress = stress_detect;

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
