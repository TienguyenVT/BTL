#include "driver/i2c.h"
#include "esp_log.h"
#include "freertos/task.h"
#include "max30105.h"
#include "spo2_algorithm.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

static const char *TAG = "MAIN";

// --- CẤU HÌNH CHÂN CHO ESP32-S3 SUPER MINI ---
#define I2C_SDA_PIN 8
#define I2C_SCL_PIN 9
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
    // 1. Collect Batch of 50 samples
    for (int i = 0; i < BATCH_SIZE; i++) {
      while (max30105_available() == false) {
        max30105_check(&sensor);
        vTaskDelay(pdMS_TO_TICKS(1)); // Min delay for speed
      }
      rawRed[i] = max30105_getRed();
      rawIr[i] = max30105_getIR();
      max30105_nextSample();
    }

    // 2. Gaussian Filtering
    // Calculate Mean & StdDev
    float redMean = calculate_mean(rawRed, BATCH_SIZE);
    float irMean = calculate_mean(rawIr, BATCH_SIZE);

    // --- CHECK FINGER ---
    // Neu cuong do IR qua thap (< 10000), tuc la chua dat tay
    if (irMean < 10000) {
      // Neu cuong do IR qua thap (< 10000), tuc la chua dat tay
      // Reset buffers de tranh du lieu cu lam anh huong khi dat tay lai
      memset(processRed, 0, sizeof(processRed));
      memset(processIr, 0, sizeof(processIr));
      continue;
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
        int avgBpm = (int)(filteredBpmSum / filteredCount);
        int avgSpo2 = (int)(filteredSpo2Sum / filteredCount);
        printf("BPM: %d, SpO2: %d%%\n", avgBpm, avgSpo2);
      }

      // Reset buffer for next 5-second window
      resultCount = 0;
      lastPrintTime = currentTime;
    }
  }
}

void app_main(void) {
  // Initialize I2C first
  i2c_master_init();

  // Create Task with increased stack size (8192 bytes)
  xTaskCreate(sensor_task, "sensor_task", 8192, NULL, 5, NULL);
}
