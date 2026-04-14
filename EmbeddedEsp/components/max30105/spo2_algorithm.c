#include "spo2_algorithm.h"
#include <stdint.h>
#include <math.h>

void maxim_heart_rate_and_oxygen_saturation(
    uint32_t *pun_ir_buffer, int32_t n_ir_buffer_length,
    uint32_t *pun_red_buffer, int32_t *pn_spo2, int8_t *pch_spo2_valid,
    int32_t *pn_heart_rate, int8_t *pch_hr_valid) {
  int32_t k;
  int32_t i;
  int32_t n_th1;
  int32_t n_npks; // number of peaks found
  int32_t an_ir_valley_locs[15];
  int32_t n_peak_interval_sum;

  int32_t an_x[100]; // x

  // --- 2ND ORDER BUTTERWORTH BANDPASS FILTER (0.5Hz - 5Hz @ 100Hz) ---

  // 1. Median Filter (3-point) - Pre-processing
  for (k = 1; k < n_ir_buffer_length - 1; k++) {
    int32_t a = -1 * pun_ir_buffer[k - 1];
    int32_t b = -1 * pun_ir_buffer[k];
    int32_t c = -1 * pun_ir_buffer[k + 1];
    int32_t median;
    if ((a <= b && b <= c) || (c <= b && b <= a))
      median = b;
    else if ((b <= a && a <= c) || (c <= a && a <= b))
      median = a;
    else
      median = c;
    an_x[k] = median;
  }
  an_x[0] = -1 * pun_ir_buffer[0];
  an_x[n_ir_buffer_length - 1] = -1 * pun_ir_buffer[n_ir_buffer_length - 1];

  // 2. Butterworth High Pass Filter (0.5Hz) - UPDATED
  // fs = 100Hz, fc = 0.5Hz, Q = 0.707
  // b = [ 0.97803048, -1.95606096,  0.97803048]
  // a = [ 1.        , -1.95557824,  0.95654368]

  float x_hp_prev[2] = {0, 0};
  float y_hp_prev[2] = {0, 0};

  // Initialize with first value to reduce transient
  x_hp_prev[0] = (float)an_x[0];
  x_hp_prev[1] = (float)an_x[0];

  for (k = 0; k < n_ir_buffer_length; k++) {
    float x_curr = (float)an_x[k];
    float y_curr = 0.97803f * x_curr - 1.95606f * x_hp_prev[0] +
                   0.97803f * x_hp_prev[1] + 1.95558f * y_hp_prev[0] -
                   0.95654f * y_hp_prev[1];

    x_hp_prev[1] = x_hp_prev[0];
    x_hp_prev[0] = x_curr;
    y_hp_prev[1] = y_hp_prev[0];
    y_hp_prev[0] = y_curr;

    an_x[k] = (int32_t)y_curr;
  }

  // 3. Butterworth Low Pass Filter (4Hz) - UPDATED
  // fs = 100Hz, fc = 4Hz
  // b = [0.0133592 , 0.0267184 , 0.0133592 ]
  // a = [1.        , -1.64745998,  0.70089678]
  float x_lp_prev[2] = {0, 0};
  float y_lp_prev[2] = {0, 0};

  // Initialize
  x_lp_prev[0] = (float)an_x[0];
  x_lp_prev[1] = (float)an_x[0];
  y_lp_prev[0] = (float)an_x[0];
  y_lp_prev[1] = (float)an_x[0];

  for (k = 0; k < n_ir_buffer_length; k++) {
    float x_curr = (float)an_x[k];
    float y_curr = 0.01336f * x_curr + 0.02672f * x_lp_prev[0] +
                   0.01336f * x_lp_prev[1] + 1.64746f * y_lp_prev[0] -
                   0.70090f * y_lp_prev[1];

    x_lp_prev[1] = x_lp_prev[0];
    x_lp_prev[0] = x_curr;
    y_lp_prev[1] = y_lp_prev[0];
    y_lp_prev[0] = y_curr;

    an_x[k] = (int32_t)y_curr;
  }

  // Calculate threshold
  n_th1 = 0;
  for (k = 0; k < n_ir_buffer_length; k++) {
    if (an_x[k] > n_th1)
      n_th1 = an_x[k];
  }
  // Tăng ngưỡng lên 1/2 biên độ max
  n_th1 = n_th1 / 2;
  if (n_th1 < 30)
    n_th1 = 30;
  if (n_th1 > 60)
    n_th1 = 60;

  // Peak (Valley) detection
  n_npks = 0;
  // Refractory period: Minimum distance between peaks to filter harmonics
  int32_t min_distance = 33; // 330ms at 100Hz
  int32_t last_peak_k = -33;

  for (k = 1; k < n_ir_buffer_length - 1; k++) {
    if (an_x[k] > n_th1 && an_x[k] > an_x[k - 1] && an_x[k] > an_x[k + 1]) {
      if ((k - last_peak_k) > min_distance) {
        an_ir_valley_locs[n_npks] = k;
        last_peak_k = k;
        n_npks++;
        if (n_npks >= 15)
          break;
      }
    }
  }

  // Calculate HR
  if (n_npks >= 2) {
    int32_t intervals[15];
    int32_t avg_interval = 0;

    // Calculate intervals
    for (k = 1; k < n_npks; k++) {
      intervals[k - 1] = (an_ir_valley_locs[k] - an_ir_valley_locs[k - 1]);
      avg_interval += intervals[k - 1];
    }
    avg_interval /= (n_npks - 1);

    // Consistency Check: Deviation > 10 samples (100ms) = Invalid
    int8_t is_consistent = 1;
    for (k = 0; k < n_npks - 1; k++) {
      if (intervals[k] > avg_interval + 10 ||
          intervals[k] < avg_interval - 10) {
        is_consistent = 0;
        break;
      }
    }

    if (is_consistent) {
      n_peak_interval_sum = avg_interval;
      *pn_heart_rate = (int32_t)(6000 / n_peak_interval_sum);
      *pch_hr_valid = 1;
    } else {
      *pn_heart_rate = -999;
      *pch_hr_valid = 0; // Rhythm irregular
    }
  } else {
    *pn_heart_rate = -999;
    *pch_hr_valid = 0;
  }

  // Calculate SpO2
  if (n_npks >= 2) {
    // Calculate DC (direct current / mean) for both channels
    int32_t n_red_mean = 0;
    int32_t n_ir_mean = 0;
    for (i = 0; i < n_ir_buffer_length; i++) {
      n_red_mean += pun_red_buffer[i];
      n_ir_mean += pun_ir_buffer[i];
    }
    n_red_mean = n_red_mean / n_ir_buffer_length;
    n_ir_mean = n_ir_mean / n_ir_buffer_length;

    // Calculate AC (alternating current / RMS of deviations) for both channels
    int32_t n_red_ac = 0;
    int32_t n_ir_ac = 0;
    for (i = 0; i < n_ir_buffer_length; i++) {
      int32_t red_diff = (int32_t)pun_red_buffer[i] - n_red_mean;
      int32_t ir_diff = (int32_t)pun_ir_buffer[i] - n_ir_mean;
      n_red_ac += red_diff * red_diff;
      n_ir_ac += ir_diff * ir_diff;
    }
    // RMS = sqrt(sum(x^2) / n)
    float red_ac = sqrt((float)n_red_ac / n_ir_buffer_length);
    float ir_ac = sqrt((float)n_ir_ac / n_ir_buffer_length);

    // Prevent division by zero
    if (n_ir_mean > 0 && n_red_mean > 0 && ir_ac > 0 && red_ac > 0) {
      // R = (AC_red / DC_red) / (AC_ir / DC_ir)
      float r = (red_ac / n_red_mean) / (ir_ac / n_ir_mean);

      // Maxim's empirical SpO2 formula (derived from look-up table)
      // SpO2 = -45.60 * R^2 + 30.354 * R + 94.845
      float spo2_f = -45.60f * r * r + 30.354f * r + 94.845f;

      // Clamp to valid physiological range [70, 100]
      if (spo2_f < 70.0f)
        spo2_f = 70.0f;
      if (spo2_f > 100.0f)
        spo2_f = 100.0f;

      *pn_spo2 = (int32_t)(spo2_f + 0.5f); // Round to nearest integer
      *pch_spo2_valid = 1;

      // Debug log for validation (can be removed in production)
      // ESP_LOGI(TAG, "SpO2: %ld, R=%.4f (red_dc=%ld, ir_dc=%ld, red_ac=%.2f, ir_ac=%.2f)",
      //          *pn_spo2, r, n_red_mean, n_ir_mean, red_ac, ir_ac);
    } else {
      *pn_spo2 = -999;
      *pch_spo2_valid = 0;
    }
  } else {
    *pn_spo2 = -999;
    *pch_spo2_valid = 0;
  }
}
