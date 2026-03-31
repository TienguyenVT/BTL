#include "gsr_sensor.h"
#include "health_data.h"
#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"
#include "driver/gpio.h"
#include "driver/touch_pad.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "GSR";
static const char *NVS_NS = "gsr_cal";

// ADC handle cho GSR
static adc_oneshot_unit_handle_t gsr_adc_handle = NULL;

// ADC handle cho biến trở calibration
static adc_oneshot_unit_handle_t cal_adc_handle = NULL;

// Timer debounce cho nút calibrate
static uint32_t s_cal_button_press_time = 0;
static bool s_cal_button_was_pressed = false;

// Lưu calibration offset vào NVS (flash)
static void save_calibration_to_nvs(health_data_t *data) {
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NS, NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(err));
        return;
    }
    nvs_set_i32(nvs, "gsr_offset", data->gsr_offset);
    nvs_set_i32(nvs, "gsr_baseline", data->gsr_baseline);
    nvs_set_i32(nvs, "calibrate_done", data->calibrate_done ? 1 : 0);
    nvs_commit(nvs);
    nvs_close(nvs);
    ESP_LOGI(TAG, "Saved to NVS: offset=%d, baseline=%d", data->gsr_offset, data->gsr_baseline);
}

// Đọc calibration offset từ NVS (khi khởi động)
static void load_calibration_from_nvs(health_data_t *data) {
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NS, NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        ESP_LOGI(TAG, "No NVS calibration data (first boot?)");
        return;
    }
    nvs_get_i32(nvs, "gsr_offset", &data->gsr_offset);
    nvs_get_i32(nvs, "gsr_baseline", &data->gsr_baseline);
    int done = 0;
    nvs_get_i32(nvs, "calibrate_done", &done);
    data->calibrate_done = (done == 1);
    nvs_close(nvs);
    ESP_LOGI(TAG, "Loaded from NVS: offset=%d, baseline=%d, done=%d",
             data->gsr_offset, data->gsr_baseline, data->calibrate_done);
}

// Đọc giá trị biến trở calibration (lấy trung bình nhiều mẫu)
static int read_calibration_pot(void) {
    if (cal_adc_handle == NULL) return 0;

    int sum = 0;
    for (int i = 0; i < CAL_POT_SAMPLE_SIZE; i++) {
        int val = 0;
        ESP_ERROR_CHECK(adc_oneshot_read(cal_adc_handle, CAL_ADC_CHANNEL, &val));
        sum += val;
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    return sum / CAL_POT_SAMPLE_SIZE;
}

// Bắt đầu calibrate: đọc GSR thực tế của user → tính offset → lưu
static void gsr_start_calibration(health_data_t *data) {
    // Đọc GSR thực tế của user (raw, chưa offset)
    int user_gsr_raw = data->gsr_raw;

    if (user_gsr_raw <= 0 || user_gsr_raw >= 4095) {
        ESP_LOGW(TAG, "Calibration failed: GSR raw=%d invalid", user_gsr_raw);
        return;
    }

    // Offset = baseline target - GSR thực tế của user
    // Nếu user GSR = 1800, offset = 2200 - 1800 = +400
    // GSR sau offset = 1800 + 400 = 2200 ✓
    data->gsr_offset = GSR_TARGET_BASELINE - user_gsr_raw;
    data->gsr_baseline = GSR_TARGET_BASELINE;  // Luôn là 2200
    data->calibrate_done = true;

    // Lưu vào NVS để không mất khi restart
    save_calibration_to_nvs(data);

    ESP_LOGI(TAG, "Calibration done! GSR_raw=%d → GSR=%d (offset=%d)",
             user_gsr_raw, data->gsr_raw + data->gsr_offset, data->gsr_offset);
}

// Khởi tạo nút nhấn calibrate (GPIO input với pull-up)
static void cal_button_init(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << CAL_BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    ESP_LOGI(TAG, "Cal button init on GPIO %d", CAL_BUTTON_PIN);
}

// Kiểm tra nút calibrate: nhấn giữ 3s → bắt đầu calibrate
// Logic: ở MODE_IDLE, nhấn giữ BOOT → vào CALIBRATE
//         Ở MODE_CALIBRATE, nhấn giữ BOOT → lưu offset
static void handle_calibration_button(health_data_t *data) {
    static uint32_t press_start_ms = 0;
    static bool was_pressed = false;

    bool is_pressed = (gpio_get_level(CAL_BUTTON_PIN) == 0);  // Active low

    if (is_pressed && !was_pressed) {
        // Bắt đầu nhấn
        press_start_ms = xTaskGetTickCount() * portTICK_PERIOD_MS;
    } else if (!is_pressed && was_pressed) {
        // Đã thả nút
        uint32_t hold_ms = xTaskGetTickCount() * portTICK_PERIOD_MS - press_start_ms;
        if (hold_ms >= CAL_BUTTON_PRESS_MS && data->gsr_raw > 0) {
            if (data->mode == MODE_IDLE) {
                // Ở IDLE → nhấn giữ → vào chế độ CALIBRATE
                data->mode = MODE_CALIBRATE;
                data->calibrate_active = true;
                data->calibrate_done = false;
                ESP_LOGI(TAG, "Entering CALIBRATE mode (hold=%ums)", hold_ms);
            } else if (data->mode == MODE_CALIBRATE && data->calibrate_active) {
                // Ở CALIBRATE → nhấn giữ → xác nhận lưu offset
                gsr_start_calibration(data);
                data->calibrate_active = false;
                data->mode = MODE_IDLE;
                ESP_LOGI(TAG, "Calibration saved, back to IDLE (hold=%ums)", hold_ms);
            }
        }
    }

    was_pressed = is_pressed;
}

void gsr_sensor_task(void *pvParameters) {
    ESP_LOGI(TAG, "GSR Sensor Task Started...");
    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    // === Đọc calibration đã lưu từ NVS ===
    load_calibration_from_nvs(data);

    // === Khởi tạo nút nhấn calibrate ===
    cal_button_init();

    // === Khởi tạo ADC cho GSR ===
    adc_oneshot_unit_init_cfg_t init_config_gsr = {
        .unit_id = GSR_ADC_UNIT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config_gsr, &gsr_adc_handle));

    adc_oneshot_chan_cfg_t gsr_config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(gsr_adc_handle, GSR_ADC_CHANNEL, &gsr_config));

    // === Khởi tạo ADC cho biến trở calibration ===
    adc_oneshot_unit_init_cfg_t init_config_cal = {
        .unit_id = CAL_ADC_UNIT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config_cal, &cal_adc_handle));

    adc_oneshot_chan_cfg_t cal_config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(cal_adc_handle, CAL_ADC_CHANNEL, &cal_config));

    ESP_LOGI(TAG, "GSR ADC=CH%d, Cal-Pot ADC=CH%d", GSR_ADC_CHANNEL, CAL_ADC_CHANNEL);

    while (1) {
        // Chờ WiFi kết nối
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        // === Kiểm tra nút calibrate (nhấn giữ 3s) ===
        handle_calibration_button(data);

        // === Đọc GSR ===
        long sum = 0;
        for (int i = 0; i < GSR_SAMPLE_SIZE; i++) {
            int analog_val;
            ESP_ERROR_CHECK(adc_oneshot_read(gsr_adc_handle, GSR_ADC_CHANNEL, &analog_val));
            if (analog_val == 0) {
                vTaskDelay(pdMS_TO_TICKS(2));
                ESP_ERROR_CHECK(adc_oneshot_read(gsr_adc_handle, GSR_ADC_CHANNEL, &analog_val));
            }
            sum += analog_val;
            vTaskDelay(pdMS_TO_TICKS(2));
        }

        int gsr_raw = sum / GSR_SAMPLE_SIZE;

        // Lưu GSR raw (chưa offset)
        data->gsr_raw = gsr_raw;

        // Nếu đã calibrate → áp dụng offset để GSR luôn về baseline 2200
        if (data->calibrate_done && data->gsr_offset != 0) {
            data->gsr = gsr_raw + data->gsr_offset;
            // Clamp để không vượt quá ADC range
            if (data->gsr < 0) data->gsr = 0;
            if (data->gsr > 4095) data->gsr = 4095;
        } else {
            // Chưa calibrate → dùng giá trị raw
            data->gsr = gsr_raw;
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
