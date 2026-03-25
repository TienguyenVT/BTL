#include "sensor_hub.h"
#include "health_data.h"
#include "max30105.h"
#include "spo2_algorithm.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <math.h>
#include <string.h>

static const char *TAG = "SENSOR_HUB";

// Mutex riêng cho từng bus I2C
SemaphoreHandle_t i2c_mutex_oled = NULL;  // Bus 0 — SSD1306
SemaphoreHandle_t i2c_mutex_max = NULL;   // Bus 1 — MAX30105

static max30105_t sensor;
static TaskHandle_t s_sensor_task_handle = NULL;

void sensor_hub_i2c_init(void) {
    // Bus I2C_NUM_0: OLED SSD1306
    i2c_config_t conf0 = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = SSD1306_SDA_PIN,
        .scl_io_num = SSD1306_SCL_PIN,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = SSD1306_I2C_SPEED,
    };
    i2c_param_config(SSD1306_I2C_PORT, &conf0);
    i2c_driver_install(SSD1306_I2C_PORT, conf0.mode, 0, 0, 0);

    // Bus I2C_NUM_1: MAX30105 (SDA=12, SCL=13)
    i2c_config_t conf1 = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = MAX30105_SDA_PIN,
        .scl_io_num = MAX30105_SCL_PIN,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = MAX30105_I2C_SPEED,
    };
    i2c_param_config(MAX30105_I2C_PORT, &conf1);
    i2c_driver_install(MAX30105_I2C_PORT, conf1.mode, 0, 0, 0);

    // Tạo mutex riêng cho từng bus
    i2c_mutex_oled = xSemaphoreCreateMutex();
    i2c_mutex_max = xSemaphoreCreateMutex();
    configASSERT(i2c_mutex_oled);
    configASSERT(i2c_mutex_max);
    ESP_LOGI(TAG, "I2C bus 0 (OLED) va I2C bus 1 (MAX30105) da khoi tao thanh cong.");
}

// --- ISR cho MAX30105 ---
static void IRAM_ATTR max30105_isr_handler(void *arg) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    vTaskNotifyGiveFromISR(s_sensor_task_handle, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

// --- Helper: Gaussian Filter ---
static float calculate_mean(uint32_t *data, int len) {
    uint64_t sum = 0;
    for (int i = 0; i < len; i++) {
        sum += data[i];
    }
    return (float)sum / len;
}

static float calculate_stddev(uint32_t *data, int len, float mean) {
    float sum_sq_diff = 0;
    for (int i = 0; i < len; i++) {
        sum_sq_diff += pow((float)data[i] - mean, 2);
    }
    return sqrt(sum_sq_diff / len);
}

void sensor_hub_task(void *pvParameters) {
    s_sensor_task_handle = xTaskGetCurrentTaskHandle();

    // Initialize MAX30105 với retry logic
    const int MAX_RETRIES = 10;
    bool sensor_ok = false;
    for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        ESP_LOGI(TAG, "Khoi tao MAX30105 (lan %d/%d)...", attempt, MAX_RETRIES);
        sensor_ok = max30105_begin(&sensor, MAX30105_I2C_PORT, 400000);
        if (sensor_ok) {
            break;
        }
        ESP_LOGW(TAG, "MAX30105 chua san sang, thu lai sau 500ms...");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
    if (!sensor_ok) {
        ESP_LOGE(TAG, "LOI: Khong tim thay MAX30105 sau %d lan thu. Kiem tra day noi!", MAX_RETRIES);
        while (1) {
            vTaskDelay(pdMS_TO_TICKS(5000));
        }
    }

    // Configure sensor
    uint8_t ledBrightness = 60;
    uint8_t sampleAverage = 1;
    uint8_t ledMode = 2;
    int sampleRate = 1000;
    int pulseWidth = 215;
    int adcRange = 8192;

    xSemaphoreTake(i2c_mutex_max, portMAX_DELAY);
    max30105_setup(&sensor, ledBrightness, sampleAverage, ledMode, sampleRate,
                   pulseWidth, adcRange);

    // Cấu hình chân ngắt (INT) cho MAX30105
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_NEGEDGE,
        .pin_bit_mask = (1ULL << MAX30105_INT_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&io_conf);

    gpio_install_isr_service(0);
    gpio_isr_handler_add(MAX30105_INT_PIN, max30105_isr_handler,
                         (void *)MAX30105_INT_PIN);

    // Kích hoạt ngắt PPG_RDY
    max30105_writeRegister8(&sensor, 0x02, 0x80);
    xSemaphoreGive(i2c_mutex_max);

    // Buffers
    const int BATCH_SIZE = 100;
    const int FILTERED_SIZE = 15;
    const int PROCESS_BUFFER_SIZE = 100;

    static uint32_t rawRed[100];
    static uint32_t rawIr[100];
    static uint32_t processRed[100];
    static uint32_t processIr[100];

    memset(processRed, 0, sizeof(processRed));
    memset(processIr, 0, sizeof(processIr));

    int32_t spo2;
    int8_t validSPO2;
    int32_t heartRate;
    int8_t validHeartRate;

    // Buffer kết quả 10 giây
    const int RESULT_BUFFER_SIZE = 200;
    static int32_t bpmBuffer[200];
    static int32_t spo2Buffer[200];
    static int resultCount = 0;
    static TickType_t lastPrintTime = 0;
    if (lastPrintTime == 0)
        lastPrintTime = xTaskGetTickCount();

    health_data_t *data = health_data_get();
    EventGroupHandle_t evt = health_data_get_event_group();

    while (1) {
        xEventGroupWaitBits(evt, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        // 1. Collect batch
        TickType_t batch_start = xTaskGetTickCount();
        const TickType_t BATCH_TIMEOUT = pdMS_TO_TICKS(5000); // Tối đa 5 giây cho 1 batch

        for (int i = 0; i < BATCH_SIZE; i++) {
            if ((xTaskGetTickCount() - batch_start) > BATCH_TIMEOUT) {
                ESP_LOGW(TAG, "Batch timeout! Thoat vong lap thu thap data.");
                break;
            }

            int wait_count = 0;
            while (max30105_available() == false) {
                if (wait_count > 50) {
                    // Nếu chờ quá lâu (>500ms) không có dữ liệu, ngắt luôn vòng for
                    ESP_LOGW(TAG, "Timeout cho 1 sample! Nguy co ket trang thai.");
                    goto exit_batch; 
                }
                
                ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(10));
                wait_count++;

                if (xSemaphoreTake(i2c_mutex_max, pdMS_TO_TICKS(50)) == pdTRUE) {
                    max30105_check(&sensor);
                    xSemaphoreGive(i2c_mutex_max);
                } else {
                    ESP_LOGW(TAG, "I2C mutex timeout, skip check");
                }
            }
            rawRed[i] = max30105_getRed();
            rawIr[i] = max30105_getIR();
            max30105_nextSample();

            // Yield mỗi 25 sample để nhả CPU cho scheduler
            if (i % 25 == 24) vTaskDelay(1);
        }
exit_batch:

        // 2. Gaussian filtering
        float redMean = calculate_mean(rawRed, BATCH_SIZE);
        float irMean = calculate_mean(rawIr, BATCH_SIZE);

        // --- SENSOR FUSION: Phát hiện User ---
        // Nâng ngưỡng IR lên 50000 để loại bỏ nhiễu môi trường. Ngón tay thật thường > 80000.
        bool ir_detected = (irMean > 50000);
        
        // Loại bỏ fallback bù trừ trừ khi IR thực sự có phản xạ. 
        // Các cảm biến GSR/Temp có thể bị nhiễu dây (ví dụ GSR=4095) gây false positive.
        bool user_present = ir_detected;

        static int warmup_skip = 0;

        if (!user_present) {
            if (data->is_user_present) {
                ESP_LOGI(TAG, "Nguoi dung vua buong tay. Chuyen sang IDLE.");
            }
            data->is_user_present = false;
            if (data->mode != MODE_CONFIG) {
                data->mode = MODE_IDLE;
            }
            // Cập nhật baseline nhiệt độ khi không có user
            if (data->room_temp > 0) {
                data->temp_baseline = data->room_temp;
            }
            memset(processRed, 0, sizeof(processRed));
            memset(processIr, 0, sizeof(processIr));
            data->bpm = 0;
            data->spo2 = 0;
            // Delay 100ms khi IDLE: đủ ngắn để không tràn FIFO (32 sample @ 1000Hz = 32ms)
            // nhưng đủ dài để nhả CPU cho idle task feed watchdog
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        } else {
            if (!data->is_user_present) {
                ESP_LOGI(TAG, "Phat hien nguoi dung. Chuyen sang ACTIVE.");
                warmup_skip = 6; // Bỏ qua 6 lượt đo đầu để chống nhiễu loạn nhịp (artifact) và chờ AGC
            }
            data->is_user_present = true;
            if (data->mode != MODE_CONFIG) {
                data->mode = MODE_ACTIVE;
            }
        }

        float redStd = calculate_stddev(rawRed, BATCH_SIZE, redMean);
        float irStd = calculate_stddev(rawIr, BATCH_SIZE, irMean);

        // Select best samples
        uint32_t filteredRedBatch[15];
        uint32_t filteredIrBatch[15];
        int filteredCount = 0;

        for (int i = 0; i < BATCH_SIZE && filteredCount < FILTERED_SIZE; i++) {
            bool redOk = (rawRed[i] >= (redMean - redStd)) &&
                         (rawRed[i] <= (redMean + redStd));
            bool irOk = (rawIr[i] >= (irMean - irStd)) &&
                        (rawIr[i] <= (irMean + irStd));
            if (redOk && irOk) {
                filteredRedBatch[filteredCount] = rawRed[i];
                filteredIrBatch[filteredCount] = rawIr[i];
                filteredCount++;
            }
        }

        while (filteredCount < FILTERED_SIZE) {
            filteredRedBatch[filteredCount] = (uint32_t)redMean;
            filteredIrBatch[filteredCount] = (uint32_t)irMean;
            filteredCount++;
        }

        // 3. Update rolling buffer
        for (int i = 0; i < PROCESS_BUFFER_SIZE - FILTERED_SIZE; i++) {
            processRed[i] = processRed[i + FILTERED_SIZE];
            processIr[i] = processIr[i + FILTERED_SIZE];
        }
        for (int i = 0; i < FILTERED_SIZE; i++) {
            processRed[PROCESS_BUFFER_SIZE - FILTERED_SIZE + i] = filteredRedBatch[i];
            processIr[PROCESS_BUFFER_SIZE - FILTERED_SIZE + i] = filteredIrBatch[i];
        }

        // 4. Calculate BPM / SpO2
        if (warmup_skip > 0) {
            warmup_skip--;
        } else {
            maxim_heart_rate_and_oxygen_saturation(processIr, PROCESS_BUFFER_SIZE,
                                                   processRed, &spo2, &validSPO2,
                                                   &heartRate, &validHeartRate);

            // 5. Store result
            if (validHeartRate && validSPO2) {
                if (heartRate > 40 && heartRate < 220 && spo2 > 50 && spo2 <= 100) {
                    if (resultCount < RESULT_BUFFER_SIZE) {
                        bpmBuffer[resultCount] = heartRate;
                        spo2Buffer[resultCount] = spo2;
                        resultCount++;
                    }
                }
            }
        }
        TickType_t currentTime = xTaskGetTickCount();
        if ((currentTime - lastPrintTime) >= pdMS_TO_TICKS(10000) && resultCount > 0) {
            float bpmMean = 0;
            for (int i = 0; i < resultCount; i++) {
                bpmMean += bpmBuffer[i];
            }
            bpmMean /= resultCount;

            float bpmStd = 0;
            for (int i = 0; i < resultCount; i++) {
                bpmStd += pow((float)bpmBuffer[i] - bpmMean, 2);
            }
            bpmStd = sqrt(bpmStd / resultCount);

            float filteredBpmSum = 0;
            float filteredSpo2Sum = 0;
            int fCount = 0;

            for (int i = 0; i < resultCount; i++) {
                if (bpmBuffer[i] >= (bpmMean - bpmStd) &&
                    bpmBuffer[i] <= (bpmMean + bpmStd)) {
                    filteredBpmSum += bpmBuffer[i];
                    filteredSpo2Sum += spo2Buffer[i];
                    fCount++;
                }
            }

            if (fCount > 0) {
                data->bpm = (int)(filteredBpmSum / fCount);
                data->spo2 = (int)(filteredSpo2Sum / fCount);
            }

            resultCount = 0;
            lastPrintTime = currentTime;
        }
    }
}
