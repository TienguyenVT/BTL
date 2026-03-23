#include "driver/i2c.h"
#include "esp_log.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "max30105.h"
#include "ds18b20.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "esp_mac.h"
#include "string.h"
#include "freertos/event_groups.h"
#include "mqtt_client.h"
#include "esp_crt_bundle.h"

esp_mqtt_client_handle_t mqtt_client = NULL;
static bool mqtt_started = false;

static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = event_data;
    switch ((esp_mqtt_event_id_t)event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI("MQTT", "Da ket noi HiveMQ Cloud");
            break;
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI("MQTT", "Mat ket noi HiveMQ Cloud");
            break;
        case MQTT_EVENT_PUBLISHED:
            ESP_LOGD("MQTT", "Gui thanh cong msg_id=%d", event->msg_id);
            break;
        case MQTT_EVENT_ERROR:
            ESP_LOGE("MQTT", "Loi doc / ghi MQTT!");
            break;
        default:
            break;
    }
}

static void mqtt_app_start(void) {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtts://6b09ec30252741efa972f3f845ce726d.s1.eu.hivemq.cloud:8883",
        .credentials.username = "Ptit1234",
        .credentials.authentication.password = "Ptit1234",
        .broker.verification.crt_bundle_attach = esp_crt_bundle_attach,
    };
    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(mqtt_client);
}

static const char *WIFI_TAG = "WIFI_AP";

// --- EVENT GROUP CHO WIFI WORKFLOW ---
EventGroupHandle_t wifi_event_group;
const int WIFI_CONNECTED_BIT = BIT0;

#include "wifi_provisioning/manager.h"
#include "wifi_provisioning/scheme_softap.h"

static void wifi_prov_event_handler(void* arg, esp_event_base_t event_base,
                                    int32_t event_id, void* event_data) {
    if (event_base == WIFI_PROV_EVENT) {
        switch (event_id) {
            case WIFI_PROV_START:
                ESP_LOGI(WIFI_TAG, "Bat dau che do Provisioning vao SoftAP IoMT-PTIT de cau hinh");
                break;
            case WIFI_PROV_CRED_RECV:
                ESP_LOGI(WIFI_TAG, "Da nhan duoc mat khau WiFi tu App!");
                break;
            case WIFI_PROV_CRED_FAIL:
                ESP_LOGI(WIFI_TAG, "Ket noi WiFi that bai! Khoi dong lai Provisioning...");
                wifi_prov_mgr_reset_provisioning();
                break;
            case WIFI_PROV_CRED_SUCCESS:
                ESP_LOGI(WIFI_TAG, "Cau hinh WiFi thanh cong!");
                break;
            case WIFI_PROV_END:
                ESP_LOGI(WIFI_TAG, "Ket thuc Provisioning hien tai.");
                wifi_prov_mgr_deinit();
                break;
            default:
                break;
        }
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(WIFI_TAG, "Da ket noi Router Internet thanh cong - IP: " IPSTR, IP2STR(&event->ip_info.ip));
        
        // MỞ KHÓA HOẠT ĐỘNG KHI ĐÃ LÊN MẠNG
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
        ESP_LOGW(WIFI_TAG, "=> Da co ket noi Internet. MO CUA cho cac cam bien hoat dong!");
        
        // Bắt đầu kết nối MQTT
        if (!mqtt_started) {
            mqtt_app_start();
            mqtt_started = true;
        }
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI(WIFI_TAG, "Mat ket noi mang. Dang thu ket noi lai...");
        
        // ĐÓNG KHÓA
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
        ESP_LOGW(WIFI_TAG, "=> Mat ket noi Internet. DUNG tiep nhan du lieu tu cam bien!");
        esp_wifi_connect();
    }
}

void wifi_init_prov(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Cần tạo cả 2 interface cho Provisioning qua SoftAP
    esp_netif_create_default_wifi_sta();
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // Đăng ký Event
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_PROV_EVENT, ESP_EVENT_ANY_ID, &wifi_prov_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_prov_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, ESP_EVENT_ANY_ID, &wifi_prov_event_handler, NULL));

    // Cấu hình Provisioning Manager (Sử dụng scheme SoftAP)
    wifi_prov_mgr_config_t config = {
        .scheme = wifi_prov_scheme_softap,
        .scheme_event_handler = WIFI_PROV_EVENT_HANDLER_NONE
    };
    ESP_ERROR_CHECK(wifi_prov_mgr_init(config));

    bool provisioned = false;
    ESP_ERROR_CHECK(wifi_prov_mgr_is_provisioned(&provisioned));

    if (!provisioned) {
        ESP_LOGI(WIFI_TAG, "Thiết bị chưa có cấu hình mạng. Đang phát SoftAP 'IoMT-PTIT' để chờ setup...");
        // Mở SoftAP tên "IoMT-PTIT", Security 0 cho phép connect phẳng qua App
        ESP_ERROR_CHECK(wifi_prov_mgr_start_provisioning(WIFI_PROV_SECURITY_0, NULL, "IoMT-PTIT", NULL));
    } else {
        ESP_LOGI(WIFI_TAG, "Đã lưu sẵn thông tin WiFi trong NVS. Đang kết nối mạng...");
        wifi_prov_mgr_deinit();
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        ESP_ERROR_CHECK(esp_wifi_start());
    }
}

// --- BIẾN TOÀN CỤC CHO HỆ THỐNG ---
static TaskHandle_t sensor_task_handle = NULL;

// Dữ liệu cảm biến tập trung
static int global_bpm = 0;
static int global_spo2 = 0;
static int global_gsr = 0;
static int global_stress = 0;
static float global_body_temp = 0.0;
static float global_room_temp = 0.0;
static bool is_user_present = false;



static void IRAM_ATTR max30105_isr_handler(void* arg) {
  BaseType_t xHigherPriorityTaskWoken = pdFALSE;
  vTaskNotifyGiveFromISR(sensor_task_handle, &xHigherPriorityTaskWoken);
  if (xHigherPriorityTaskWoken) {
    portYIELD_FROM_ISR();
  }
}

#include "spo2_algorithm.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

static const char *TAG = "MAIN";

// --- CẤU HÌNH CHÂN CHO ESP32-S3 SUPER MINI ---
#define I2C_SDA_PIN 12
#define I2C_SCL_PIN 13
#define MAX30105_INT_PIN 11
#define I2C_PORT I2C_NUM_0

max30105_t sensor;

void i2c_master_init() {
  i2c_config_t conf = {
      .mode = I2C_MODE_MASTER,
      .sda_io_num = I2C_SDA_PIN,
      .scl_io_num = I2C_SCL_PIN,
      .sda_pullup_en = GPIO_PULLUP_ENABLE,
      .scl_pullup_en = GPIO_PULLUP_ENABLE,
      .master.clk_speed = 400000,
  };
  i2c_param_config(I2C_PORT, &conf);
  i2c_driver_install(I2C_PORT, conf.mode, 0, 0, 0);
}

// --- CẤU HÌNH GSR (STRESS MONITOR) ---
#define GSR_PIN GPIO_NUM_4
#define GSR_ADC_UNIT ADC_UNIT_1
#define GSR_ADC_CHANNEL ADC_CHANNEL_3 // GPIO 4 on ESP32-S3 is ADC1_CH3
#define GSR_SAMPLE_SIZE 20
#define GSR_BASELINE 2330
#define GSR_THRESHOLD_STRESS 100

void gsr_task(void *pvParameters) {
    ESP_LOGI(TAG, "GSR Sensor Task Started...");
    
    // Khởi tạo ADC oneshot
    adc_oneshot_unit_handle_t adc1_handle;
    adc_oneshot_unit_init_cfg_t init_config1 = {
        .unit_id = GSR_ADC_UNIT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config1, &adc1_handle));

    // Cấu hình kênh ADC 3 (GPIO 4)
    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,       // 12-bit mặc định
        .atten = ADC_ATTEN_DB_12,               // Suy hao 12dB (Tiêu chuẩn mới của ESP-IDF v5)
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc1_handle, GSR_ADC_CHANNEL, &config));

    while (1) {
        // Chờ đến khi có ít nhất 1 Client kết nối WiFi mới cho phép chạy tiếp
        xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        long sum = 0;

        // 1. THUẬT TOÁN LỌC NHIỄU (AVERAGING FILTER)
        for (int i = 0; i < GSR_SAMPLE_SIZE; i++) {
            int analog_val;
            ESP_ERROR_CHECK(adc_oneshot_read(adc1_handle, GSR_ADC_CHANNEL, &analog_val));
            sum += analog_val;
            vTaskDelay(pdMS_TO_TICKS(2));
        }

        int gsr_average = sum / GSR_SAMPLE_SIZE;

        // 2. PHÁT HIỆN STRESS
        int stress_detect = 0;
        if (gsr_average > (GSR_BASELINE + GSR_THRESHOLD_STRESS)) {
            stress_detect = 4000;
        }

        // 3. CẬP NHẬT DỮ LIỆU TOÀN CỤC
        global_gsr = gsr_average;
        global_stress = stress_detect;

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

// --- Helper Functions for Gaussian Filter ---
float calculate_mean(uint32_t *data, int len) {
  uint64_t sum = 0;
  for (int i = 0; i < len; i++) {
    sum += data[i];
  }
  return (float)sum / len;
}

float calculate_stddev(uint32_t *data, int len, float mean) {
  float sum_sq_diff = 0;
  for (int i = 0; i < len; i++) {
    sum_sq_diff += pow((float)data[i] - mean, 2);
  }
  return sqrt(sum_sq_diff / len);
}

void sensor_task(void *pvParameters) {
  // Lưu lại handle của task xử lý cảm biến để gọi từ ISR
  sensor_task_handle = xTaskGetCurrentTaskHandle();

  // Initialize sensor
  if (!max30105_begin(&sensor, I2C_PORT, 400000)) {
    ESP_LOGE(TAG, "LOI: Khong tim thay MAX30102. Kiem tra day noi!");
    while (1) {
      vTaskDelay(100);
    }
  }

  // Configure sensor
  uint8_t ledBrightness = 60;
  uint8_t sampleAverage = 1; // Direct raw sampling
  uint8_t ledMode = 2;
  int sampleRate = 1000; // High speed sampling 1000Hz
  int pulseWidth = 215;  // Must be lower for high sample rates
  int adcRange = 8192;

  max30105_setup(&sensor, ledBrightness, sampleAverage, ledMode, sampleRate,
                 pulseWidth, adcRange);

  // Cấu hình chân ngắt (INT) GPIO 11 cho MAX30105
  gpio_config_t io_conf = {
      .intr_type = GPIO_INTR_NEGEDGE, // Mức thấp khi có dữ liệu mới từ cảm biến
      .pin_bit_mask = (1ULL << MAX30105_INT_PIN),
      .mode = GPIO_MODE_INPUT,
      .pull_up_en = GPIO_PULLUP_ENABLE,
      .pull_down_en = GPIO_PULLDOWN_DISABLE,
  };
  gpio_config(&io_conf);
  
  // Cài đặt dịch vụ ngắt GPIO
  gpio_install_isr_service(0);
  gpio_isr_handler_add(MAX30105_INT_PIN, max30105_isr_handler, (void*) MAX30105_INT_PIN);

  // Kích hoạt ngắt phần cứng PPG_RDY trên MAX30105 (Thanh ghi ENABLE1 (0x02), Bit 7)
  max30105_writeRegister8(&sensor, 0x02, 0x80);

  // Buffer Process Variables (static to avoid stack overflow)
  const int BATCH_SIZE = 100;
  const int FILTERED_SIZE = 15;
  const int PROCESS_BUFFER_SIZE = 100;

  static uint32_t rawRed[100];
  static uint32_t rawIr[100];

  // Main processing buffer (shifted window)
  static uint32_t processRed[100];
  static uint32_t processIr[100];

  // Clear buffers
  memset(processRed, 0, sizeof(processRed));
  memset(processIr, 0, sizeof(processIr));

  int32_t spo2;
  int8_t validSPO2;
  int32_t heartRate;
  int8_t validHeartRate;

  // --- BUFFER CHO KET QUA 10 GIAY (static to avoid stack overflow) ---
  const int RESULT_BUFFER_SIZE = 200; // Du cho ~80 ket qua trong 10 giay
  static int32_t bpmBuffer[200];
  static int32_t spo2Buffer[200];
  static int resultCount = 0;
  static TickType_t lastPrintTime = 0;
  if (lastPrintTime == 0)
    lastPrintTime = xTaskGetTickCount();

  while (1) {
    // Chờ đến khi có ít nhất 1 Client kết nối WiFi mới cho phép chạy tiếp
    xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

    // 1. Collect Batch of 50 samples
    for (int i = 0; i < BATCH_SIZE; i++) {
        while (max30105_available() == false) {
            // Thay vì delay 1ms liên tục, task sẽ "ngủ" chờ ISR đánh thức
            // Giảm cực nhiều tải CPU cho hệ thống
            ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(10)); // Giảm timeout xuống 10ms để tránh rớt mẫu nếu đứt dây INT
            max30105_check(&sensor);
        }
      rawRed[i] = max30105_getRed();
      rawIr[i] = max30105_getIR();
      max30105_nextSample();
    }

    // 2. Gaussian Filtering
    // Calculate Mean & StdDev
    float redMean = calculate_mean(rawRed, BATCH_SIZE);
    float irMean = calculate_mean(rawIr, BATCH_SIZE);

    // --- CHECK FINGER (SENSOR FUSION CẬP NHẬT TRẠNG THÁI) ---
    // Neu cuong do IR qua thap (< 10000), tuc la chua dat tay
    if (irMean < 10000) {
      if (is_user_present) {
          ESP_LOGI(TAG, "Nguoi dung vua buong tay. Chuyen ve do nhiet do phong (Idle).");
      }
      is_user_present = false;
      
      // Reset buffers de tranh du lieu cu lam anh huong khi dat tay lai
      memset(processRed, 0, sizeof(processRed));
      memset(processIr, 0, sizeof(processIr));
      vTaskDelay(pdMS_TO_TICKS(1000)); // Delay 1 giay neu chua dat tay do bi nhiễu log
      continue;
    } else {
      if (!is_user_present) {
          ESP_LOGI(TAG, "Phat hien nguoi dung. Kich hoat hieu chuan nhiet do (Active).");
      }
      is_user_present = true;
    }

    float redStd = calculate_stddev(rawRed, BATCH_SIZE, redMean);
    float irStd = calculate_stddev(rawIr, BATCH_SIZE, irMean);

    // Select 15 best samples
    uint32_t filteredRedBatch[FILTERED_SIZE];
    uint32_t filteredIrBatch[FILTERED_SIZE];

    int filteredCount = 0;

    // Simplistic selection: Take first 15 that qualify, or fill with mean/last
    // valid if not enough
    for (int i = 0; i < BATCH_SIZE && filteredCount < FILTERED_SIZE; i++) {
      // Check if within 1 sigma (Mean - StdDev <= val <= Mean + StdDev)
      bool redOk = (rawRed[i] >= (redMean - redStd)) &&
                   (rawRed[i] <= (redMean + redStd));
      bool irOk =
          (rawIr[i] >= (irMean - irStd)) && (rawIr[i] <= (irMean + irStd));

      if (redOk && irOk) {
        filteredRedBatch[filteredCount] = rawRed[i];
        filteredIrBatch[filteredCount] = rawIr[i];
        filteredCount++;
      }
    }

    // Fallback if not enough samples found (unlikely but safe to handle)
    while (filteredCount < FILTERED_SIZE) {
      filteredRedBatch[filteredCount] = (uint32_t)redMean;
      filteredIrBatch[filteredCount] = (uint32_t)irMean;
      filteredCount++;
    }

    // 3. Update Rolling Process Buffer
    // Shift old data to left by FILTERED_SIZE
    for (int i = 0; i < PROCESS_BUFFER_SIZE - FILTERED_SIZE; i++) {
      processRed[i] = processRed[i + FILTERED_SIZE];
      processIr[i] = processIr[i + FILTERED_SIZE];
    }

    // Append new filtered data to the end
    for (int i = 0; i < FILTERED_SIZE; i++) {
      processRed[PROCESS_BUFFER_SIZE - FILTERED_SIZE + i] = filteredRedBatch[i];
      processIr[PROCESS_BUFFER_SIZE - FILTERED_SIZE + i] = filteredIrBatch[i];
    }

    // 4. Calculate BPM / SpO2
    maxim_heart_rate_and_oxygen_saturation(processIr, PROCESS_BUFFER_SIZE,
                                           processRed, &spo2, &validSPO2,
                                           &heartRate, &validHeartRate);

    // 5. Store Result in Buffer (instead of printing immediately)
    if (validHeartRate && validSPO2) {
      if (heartRate > 40 && heartRate < 220 && spo2 > 50 && spo2 <= 100) {
        if (resultCount < RESULT_BUFFER_SIZE) {
          bpmBuffer[resultCount] = heartRate;
          spo2Buffer[resultCount] = spo2;
          resultCount++;
        }
      }
    }

    // 6. Check if 10 seconds have passed
    TickType_t currentTime = xTaskGetTickCount();
    if ((currentTime - lastPrintTime) >= pdMS_TO_TICKS(10000) &&
        resultCount > 0) {
      // Apply Gaussian Filter to BPM buffer
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

      // Select values within Mean +/- StdDev and calculate average
      float filteredBpmSum = 0;
      float filteredSpo2Sum = 0;
      int filteredCount = 0;

      for (int i = 0; i < resultCount; i++) {
        if (bpmBuffer[i] >= (bpmMean - bpmStd) &&
            bpmBuffer[i] <= (bpmMean + bpmStd)) {
          filteredBpmSum += bpmBuffer[i];
          filteredSpo2Sum += spo2Buffer[i];
          filteredCount++;
        }
      }

      if (filteredCount > 0) {
        global_bpm = (int)(filteredBpmSum / filteredCount);
        global_spo2 = (int)(filteredSpo2Sum / filteredCount);
      }

      // Reset buffer for next 5-second window
      resultCount = 0;
      lastPrintTime = currentTime;
    }
  }
}

// --- CẤU HÌNH NHIỆT ĐỘ DS18B20 ---
#define DS18B20_PIN GPIO_NUM_3
#define TEMP_OFFSET 4.5f        // Độ lệch bù trừ ước tính (Ngón tay thường thấp hơn vùng lõi cơ thể ~4.5 độ)
#define TEMP_MULTIPLIER 1.0f    // Hệ số nhân tỷ lệ (mặc định 1.0)
#define TEMP_SMOOTH_SAMPLES 2   // Giảm xuống 2 để dải nhiệt độ phản ứng cực nhanh (không bị kéo lê)
#define TEMP_PREDICT_FACTOR 3.0f // Hệ số dự đoán gia tốc (K) giúp nhiệt độ vọt/hạ nhanh khi có thay đổi

void ds18b20_task(void *pvParameters) {
    ESP_LOGI(TAG, "DS18B20 Task Started...");
    ds18b20_init(DS18B20_PIN);

    float temp_buffer[TEMP_SMOOTH_SAMPLES] = {0};
    int sample_index = 0;
    int valid_count = 0;
    
    float prev_avg = 0;

    while (1) {
        // Chờ đến khi có ít nhất 1 Client kết nối WiFi mới cho phép chạy tiếp
        xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        float raw_temp = ds18b20_get_temp();
        if (raw_temp > -100.0) { // Nếu đọc hợp lệ
            // Đưa mẫu mới vào bộ đệm vòng (circular buffer)
            temp_buffer[sample_index] = raw_temp;
            sample_index = (sample_index + 1) % TEMP_SMOOTH_SAMPLES;
            if (valid_count < TEMP_SMOOTH_SAMPLES) valid_count++;

            // 1. Tính trung bình mẫu (Moving Average)
            float sum = 0;
            for (int i = 0; i < valid_count; i++) {
                sum += temp_buffer[i];
            }
            float avg_temp = sum / valid_count;
            
            // Phân tách Logic dựa trên trạng thái người dùng
            if (is_user_present) {
                // Người dùng đang đo: Kích hoạt thuật toán tính thân nhiệt
                float derivative = 0;
                if (valid_count >= TEMP_SMOOTH_SAMPLES && prev_avg > 0) {
                    derivative = avg_temp - prev_avg;
                }
                float boosted_temp = avg_temp + (derivative * TEMP_PREDICT_FACTOR);
                global_body_temp = (boosted_temp * TEMP_MULTIPLIER) + TEMP_OFFSET;
                
                // Lưu ý: Lúc này `global_room_temp` sẽ KHÔNG cập nhật, nó được "đóng băng" ở mốc thời gian trước khi ngón tay bạn chạm vào cảm biến.
            } else {
                // Người dùng bỏ tay ra: Tính lại nhiệt độ môi trường
                global_room_temp = avg_temp;
                // Có thể reset global_body_temp = 0.0 ở đây nếu bạn muốn, nhưng để nguyên cũng không sao vì đã có is_user_present làm cờ báo.
            }

            prev_avg = avg_temp;
        } else {
            ESP_LOGW(TAG, "Lỗi đọc DS18B20 (kiểm tra dây nối hoặc điện trở kéo)");
        }
        
        // Cảm biến mất 750ms để đọc, ta chỉ delay 1000ms (1s) để phản hồi nhanh nhất có thể
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void monitor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Monitor Task Started...");
    while (1) {
        // Đảm bảo không in log rác ra Serial khi chưa có User dùng WiFi
        xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

        // In ra tất cả dữ liệu cùng lúc để Serial Plotter vẽ biểu đồ chung
        // hoặc dễ dàng quan sát trên Device Monitor
        printf("BPM:%d,SpO2:%d,GSR:%d,Stress:%d,Baseline:%d,RoomTemp:%.2f,BodyTemp:%.2f\n", 
               global_bpm, global_spo2, global_gsr, global_stress, GSR_BASELINE, global_room_temp, global_body_temp);
        
        // Đẩy dữ liệu qua MQTT
        if (mqtt_client != NULL && mqtt_started) {
            char payload[200];
            snprintf(payload, sizeof(payload), "{\"room_temp\": %.1f, \"body_temp\": %.1f, \"bpm\": %d, \"gsr\": %d, \"stress\": %d}", 
                     global_room_temp, global_body_temp, global_bpm, global_gsr, global_stress);
            int msg_id = esp_mqtt_client_publish(mqtt_client, "ptit/health/data", payload, 0, 0, 0);
            if (msg_id != -1) {
                ESP_LOGI("MAIN", "MQTT Pub: %s", payload);
            }
        }

        // Tốc độ cập nhật console 5s (5000ms) 1 lần
        vTaskDelay(pdMS_TO_TICKS(5000)); 
    }
}

void app_main(void) {
  // Khoi tao NVS cho WiFi
  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);

  // Khoi tao Event Group de lock Sensor Tasks
  wifi_event_group = xEventGroupCreate();

  // Khoi tao WiFi Provisioning qua App
  ESP_LOGI(TAG, "Khoi dong trinh quan ly WiFi...");
  wifi_init_prov();

  // Initialize I2C first
  i2c_master_init();

  // Create Sensors Tasks
  xTaskCreate(sensor_task, "sensor_task", 8192, NULL, 5, NULL);
  xTaskCreate(gsr_task, "gsr_task", 4096, NULL, 5, NULL);
  xTaskCreate(ds18b20_task, "ds18b20_task", 4096, NULL, 5, NULL);
  
  // Create Monitor Task
  xTaskCreate(monitor_task, "monitor_task", 4096, NULL, 4, NULL);
}
