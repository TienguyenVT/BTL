#include "thermal_processor.h"
#include "health_data.h"
#include <string.h>
#include <math.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "THERMAL";

// ---------------------------------------------------------
// TẦNG PREDICTOR: BA ĐIỂM NGOẠI SUY (THREE-POINT EXTRAPOLATION)
// ---------------------------------------------------------
static void thermal_predictor_reset(thermal_predictor_t *p) {
    memset(p, 0, sizeof(*p));
    p->t_inf_stable = 0.0f;
    p->is_stable    = false;
}

static void thermal_predictor_feed(thermal_predictor_t *p, float t_skin, uint32_t now_tick) {
    // Rate-limit: chỉ lấy mẫu mỗi PRED_SAMPLE_MS
    if (p->count > 0 && (now_tick - p->last_sample_tick) < pdMS_TO_TICKS(PRED_SAMPLE_MS))
        return;

    p->temps[p->head] = t_skin;
    p->ticks[p->head] = now_tick;
    p->head = (p->head + 1) % PRED_BUF_SIZE;
    if (p->count < PRED_BUF_SIZE) p->count++;
    p->last_sample_tick = now_tick;

    if (p->count < PRED_MIN_POINTS) return;

    // Lấy 3 điểm: đầu buffer, giữa, cuối
    int n = p->count;
    int i1 = (p->head - n + PRED_BUF_SIZE) % PRED_BUF_SIZE;
    int i2 = (p->head - n/2 + PRED_BUF_SIZE) % PRED_BUF_SIZE;
    int i3 = (p->head - 1 + PRED_BUF_SIZE) % PRED_BUF_SIZE;

    float T1 = p->temps[i1];
    float T2 = p->temps[i2];
    float T3 = p->temps[i3];

    float denom = T1 + T3 - 2.0f * T2;

    // Mẫu số quá nhỏ = đường cong gần phẳng = đã hội tụ, dùng T3 luôn
    if (fabsf(denom) < 0.08f) {
        p->t_inf_history[p->hist_idx % 3] = T3;
    } else {
        float t_inf_raw = (T1 * T3 - T2 * T2) / denom;

        // Loại bỏ kết quả phi sinh lý
        if (t_inf_raw < PRED_PHY_MIN || t_inf_raw > PRED_PHY_MAX) return;

        p->t_inf_history[p->hist_idx % 3] = t_inf_raw;
    }
    p->hist_idx++;

    // Chỉ kết luận ổn định khi 3 lần predict liên tiếp đồng thuận
    if (p->hist_idx >= 3) {
        float h0 = p->t_inf_history[0];
        float h1 = p->t_inf_history[1];
        float h2 = p->t_inf_history[2];
        float spread = fmaxf(fmaxf(h0,h1),h2) - fminf(fminf(h0,h1),h2);

        if (spread < PRED_STABLE_ERR) {
            p->t_inf_stable = (h0 + h1 + h2) / 3.0f;
            p->is_stable    = true;
            ESP_LOGI(TAG, "T_inf stable: %.2f°C (spread=%.3f) after %d samples",
                     p->t_inf_stable, spread, p->count);
        }
    }
}

static float thermal_predictor_get(const thermal_predictor_t *p, float t_skin_current) {
    if (!p->is_stable) return t_skin_current;

    // Blend nhẹ về T_inf_stable, không nhảy đột ngột
    // Weight = 0.6 để vẫn phản ánh measurement thực
    return 0.6f * p->t_inf_stable + 0.4f * t_skin_current;
}


void thermal_processor_init(thermal_processor_t *tp) {
    memset(tp, 0, sizeof(thermal_processor_t));
    
    tp->kalman.x = 25.0f; // Giả sử khởi tạo ~25 độ C (nhiệt độ phòng)
    tp->kalman.P = 1.0f;
    tp->kalman.Q = KALMAN_Q;
    tp->kalman.R = KALMAN_R;
    
    tp->ema_initialized = false;
    tp->room_temp_locked = 25.0f;
    tp->current_room_temp = 25.0f;
    tp->current_body_temp = 0.0f;
    
    tp->state = THERMAL_STATE_IDLE;
    
    // Dual-sensor fusion
    tp->dht11_bias_correction = 0.0f;
    tp->prev_skin_temp = 0.0f;
    tp->confidence = 0;
    
    thermal_predictor_reset(&tp->predictor);
    tp->prediction_ready = false;
}

// ---------------------------------------------------------
// TẦNG 0: WARM START
// ---------------------------------------------------------
static void on_touch_detected(thermal_processor_t *tp, float t_ambient) {
    // Thay vì để Kalman bắt đầu từ room_temp (~27°C),
    // inject prior sinh lý hợp lý ngay lập tức
    float warm_prior = t_ambient + WARM_START_OFFSET;

    // Clamp trong range sinh lý hợp lệ
    warm_prior = fmaxf(32.0f, fminf(38.0f, warm_prior));

    tp->kalman.x = warm_prior;
    tp->kalman.P = WARM_START_VARIANCE;  // uncertainty cao → Kalman tin measurement hơn

    tp->touch_start_tick = xTaskGetTickCount();
    tp->prediction_ready = false;

    thermal_predictor_reset(&tp->predictor);
    tp->ema_initialized = false; // Bắt đầu smooth lại

    ESP_LOGI(TAG, "Warm start: prior=%.1f°C (ambient=%.1f + %.1f)",
             warm_prior, t_ambient, WARM_START_OFFSET);
}


// ---------------------------------------------------------
// TẦNG 1: LỌC MEDIAN (LOẠI BỎ SPIKE NHIỄU)
// ---------------------------------------------------------
static float apply_median_filter(thermal_processor_t *tp, float new_val) {
    tp->median_buf[tp->median_idx] = new_val;
    tp->median_idx = (tp->median_idx + 1) % MEDIAN_WINDOW_SIZE;
    
    if (tp->median_idx == 0) {
        tp->median_filled = true;
    }
    
    int count = tp->median_filled ? MEDIAN_WINDOW_SIZE : tp->median_idx;
    if (count == 0) return new_val;

    float sorted[MEDIAN_WINDOW_SIZE];
    for (int i = 0; i < count; i++) {
        sorted[i] = tp->median_buf[i];
    }
    
    // Bubble sort đơn giản
    for (int i = 0; i < count - 1; i++) {
        for (int j = 0; j < count - 1 - i; j++) {
            if (sorted[j] > sorted[j+1]) {
                float tmp = sorted[j];
                sorted[j] = sorted[j+1];
                sorted[j+1] = tmp;
            }
        }
    }
    return sorted[count / 2];
}

// ---------------------------------------------------------
// TẦNG 2: BỘ LỌC KALMAN (LỌC MỊN THEO PHƯƠNG SAI)
// ---------------------------------------------------------
static float apply_kalman_filter(kalman_filter_t *k, float measurement) {
    // 1. Dự đoán (Predict)
    k->P = k->P + k->Q;
    
    // 2. Cập nhật (Update)
    float K_gain = k->P / (k->P + k->R);
    k->x = k->x + K_gain * (measurement - k->x);
    k->P = (1.0f - K_gain) * k->P;
    
    return k->x;
}

// ---------------------------------------------------------
// TẦNG 3: ADAPTIVE EMA (LÀM MƯỢT TÍN HIỆU ĐỘNG)
// Alpha thích ứng theo rate of change — bắt signal nhanh
// khi người vừa đặt tay, lọc mạnh khi ổn định
// ---------------------------------------------------------
static float apply_adaptive_ema(thermal_processor_t *tp, float new_sample) {
    if (!tp->ema_initialized) {
        tp->ema_val = new_sample;
        tp->prev_ema_val = new_sample;
        tp->ema_initialized = true;
        return new_sample;
    }
    
    tp->prev_ema_val = tp->ema_val; // Lưu lại để tính dT
    
    float rate = fabsf(new_sample - tp->ema_val);
    
    // Adaptive alpha dựa trên rate of change (cải tiến B)
    float alpha;
    if (rate > 0.5f) {
        alpha = 0.40f;   // Thay đổi nhanh → bắt signal
    } else if (rate > 0.2f) {
        alpha = 0.20f;   // Trung bình
    } else {
        alpha = 0.08f;   // Ổn định → lọc noise mạnh
    }
    
    tp->ema_val = alpha * new_sample + (1.0f - alpha) * tp->ema_val;
    
    return tp->ema_val;
}

// ---------------------------------------------------------
// TẦNG 4a: SENSOR FUSION — BIAS CORRECTION (Vấn đề 1)
// Khi IDLE: DS18B20 đo ≈ nhiệt phòng. So sánh với DHT11 để
// học dần bias correction cho DHT11 (sai số ±2°C)
// ---------------------------------------------------------
static void update_ambient_bias(thermal_processor_t *tp, float t_ds18b20_idle, float t_dht11_ema) {
    float divergence = t_ds18b20_idle - t_dht11_ema;
    if (fabsf(divergence) < MAX_SENSOR_DIVERGENCE) {
        // Học bias dần dần — chỉ khi 2 sensor agree trong ngưỡng hợp lý
        tp->dht11_bias_correction += BIAS_CORRECTION_ALPHA * divergence;
    } else {
        // 2 sensor không đồng thuận — có thể sensor lỗi
        ESP_LOGW(TAG, "Sensor divergence %.1f°C — check sensors", divergence);
    }
}

static float get_corrected_ambient(thermal_processor_t *tp, float t_dht11_ema) {
    return t_dht11_ema + tp->dht11_bias_correction;
}

// ---------------------------------------------------------
// TẦNG 4b: TÍNH HỆ SỐ K THÍCH ỨNG (Vấn đề 2)
// k phụ thuộc humidity (tản nhiệt bay hơi) + nhiệt độ môi
// trường (co mạch ngoại vi / vasoconstriction)
// ---------------------------------------------------------
static float compute_k_dynamic(int humidity, float t_ambient) {
    // Nhân tố độ ẩm: clamp [0.85, 1.15]
    float h_clamped = fmaxf(0.0f, fminf(100.0f, (float)humidity));
    float humidity_factor = 1.0f - (h_clamped - 50.0f) * HUMIDITY_K_SENSITIVITY;
    humidity_factor = fmaxf(0.85f, fminf(1.15f, humidity_factor));

    // Nhân tố co mạch: khi trời lạnh, gradient T_skin↔T_core tăng
    float vaso_factor = 1.0f;
    if (t_ambient < VASOCONSTRICTION_THRESHOLD) {
        float cold_delta = VASOCONSTRICTION_THRESHOLD - t_ambient;
        vaso_factor = 1.0f + cold_delta * VASOCONSTRICTION_FACTOR;
        vaso_factor = fminf(vaso_factor, 1.25f);  // clamp tối đa +25%
    }

    return THERMAL_K_BASE * humidity_factor * vaso_factor;
}

// ---------------------------------------------------------
// TẦNG 4c: KIỂM TRA SINH LÝ (Vấn đề 3)
// Gate kiểm tra T_skin nằm trong phạm vi hợp lệ VÀ đã cân
// bằng nhiệt (rate of change đủ nhỏ)
// ---------------------------------------------------------
static measurement_quality_t assess_measurement_quality(float t_skin, float dt_skin_dt) {
    if (t_skin < T_SKIN_MIN_VALID || t_skin > T_SKIN_MAX_VALID)
        return MEAS_QUALITY_INVALID;
    if (fabsf(dt_skin_dt) > SKIN_STABILITY_RATE)
        return MEAS_QUALITY_UNSTABLE;
    return MEAS_QUALITY_GOOD;
}

// ---------------------------------------------------------
// TẦNG 4d: BÙ NHIỆT ĐỘNG (DUAL-SENSOR COMPENSATION)
// T_core = T_skin + k_dynamic × (T_skin − T_ambient)
// ---------------------------------------------------------
typedef enum {
    BODY_TEMP_VALID,       // ổn định, trong ngưỡng sinh lý
    BODY_TEMP_CONVERGING,  // đang hội tụ, chưa đáng tin hoàn toàn
    BODY_TEMP_ERROR        // thực sự lỗi (âm, > 45°C, sensor rời tay)
} body_temp_quality_t;

static body_temp_quality_t compute_body_temp(float t_skin, float t_ambient,
                                              int humidity, float *out_compensated) {
    if (t_skin < 20.0f || t_skin > 45.0f) {
        *out_compensated = 0.0f;
        return BODY_TEMP_ERROR;
    }

    float compensated;
    if (t_ambient < 10.0f || t_ambient > 40.0f) {
        // Fallback offset cố định nếu nhiệt độ phòng không hợp lệ
        compensated = (t_skin > 30.0f) ? t_skin + 4.5f : t_skin;
    } else {
        // Hệ số k thích ứng theo humidity + vasoconstriction
        float k = compute_k_dynamic(humidity, t_ambient);
        compensated = t_skin + k * (t_skin - t_ambient);
    }
    
    *out_compensated = compensated;

    if (compensated >= BODY_TEMP_MIN && compensated <= BODY_TEMP_MAX) {
        return BODY_TEMP_VALID; // Nằm trong khoảng hợp lý của cơ thể
    } else if (compensated >= 20.0f && compensated < BODY_TEMP_MIN) {
        return BODY_TEMP_CONVERGING; // Đang ấm lên dần, cứ cho qua
    } else {
        return BODY_TEMP_ERROR; // Hoàn toàn sai lệch
    }
}

// ---------------------------------------------------------
// TẦNG 5: KIỂM TRA ĐỘ ỔN ĐỊNH
// ---------------------------------------------------------
typedef enum { TEMP_CONVERGING, TEMP_STABLE } temp_stability_t;

static temp_stability_t check_stability(thermal_processor_t *tp, float current, float *out_val) {
    if (fabsf(current - tp->last_stable) < STABLE_THRESHOLD) {
        if (++tp->stable_count >= STABLE_COUNT_REQ) {
            tp->is_stable = true;
            *out_val = current;
            return TEMP_STABLE;
        }
    } else {
        tp->stable_count = 0;
        tp->is_stable = false;
    }
    tp->last_stable = current;
    
    // Vẫn trả về giá trị đang hội tụ cho UI
    *out_val = current;
    return TEMP_CONVERGING;
}

// ---------------------------------------------------------
// TẦNG 6: TÍNH CONFIDENCE SCORE (Cải tiến A)
// ---------------------------------------------------------
static uint8_t compute_confidence(measurement_quality_t mq, temp_stability_t st,
                                   float bias, body_temp_quality_t bq, const thermal_predictor_t *p) {
    if (mq == MEAS_QUALITY_INVALID || bq == BODY_TEMP_ERROR)
        return 0;

    uint8_t score = 0;
    
    // Base score from predictor status
    if (p->is_stable) score = 100;
    else if (p->count >= PRED_MIN_POINTS) score = 75;
    else score = 50;

    // Penalty for unstability or diverging
    if (mq == MEAS_QUALITY_UNSTABLE) score -= 10;
    if (st == TEMP_CONVERGING) score -= 5;
    if (fabsf(bias) > 1.0f) score -= 5;

    return (score > 100) ? 100 : score;
}

// =========================================================
// HÀM XỬ LÝ CHÍNH ĐƯỢC GỌI MỖI CHU KỲ BỞI TASK
// =========================================================
void thermal_processor_update(thermal_processor_t *tp, float raw_temp, bool is_user_present,
                              float ambient_temp_dht11, int humidity) {
    if (raw_temp <= -100.0f) {
        return; // Lỗi đọc cảm biến I2C/OneWire (dữ liệu rác)
    }

    // 1. Lọc nhiễu tĩnh & động
    float median_val = apply_median_filter(tp, raw_temp);
    float kalman_val = apply_kalman_filter(&tp->kalman, median_val);
    float smooth_val = apply_adaptive_ema(tp, kalman_val);

    // Tính dT/dt cho T_skin (dùng cho physiological gate)
    float dt_skin_dt = 0.0f;
    if (tp->prev_skin_temp > 0.0f) {
        dt_skin_dt = smooth_val - tp->prev_skin_temp; // °C/chu_kỳ (≈ °C/s với 1s interval)
    }
    tp->prev_skin_temp = smooth_val;

    // Lấy ambient đã hiệu chỉnh bias
    float corrected_ambient = get_corrected_ambient(tp, ambient_temp_dht11);

    // 2. State Machine quản lý chế độ (Phòng / Chạm tay / Nguội dần)
    switch(tp->state) {
        case THERMAL_STATE_IDLE:
            tp->current_room_temp = smooth_val;
            tp->room_temp_locked = smooth_val; // Chốt môi trường để dành bù nhiệt
            tp->current_body_temp = 0.0f;      // Không đo người
            tp->confidence = 0;

            // Sensor fusion: học bias DHT11 khi IDLE (Vấn đề 1)
            update_ambient_bias(tp, smooth_val, ambient_temp_dht11);
            
            if (is_user_present) {
                // Sang trạng thái ACTIVE: người dùng bắt đầu chạm tay
                tp->state = THERMAL_STATE_ACTIVE;
                tp->stable_count = 0;
                tp->is_stable = false;
                on_touch_detected(tp, corrected_ambient);
            }
            break;
            
        case THERMAL_STATE_ACTIVE:
            if (!is_user_present) {
                // Người dùng nhả tay → vào trạng thái chờ nguội
                tp->state = THERMAL_STATE_COOLDOWN;
                tp->cooldown_timer = 120; // 120 chu kỳ × 1s ≈ 120 giây
                tp->current_body_temp = 0.0f;
                tp->confidence = 0;
                break;
            }
            
            // === PHYSIOLOGICAL GATE (Vấn đề 3) ===
            measurement_quality_t mq = assess_measurement_quality(smooth_val, dt_skin_dt);
            
            // Xử lý bù độ trễ (Asymptotic Prediction)
            float dT = smooth_val - tp->prev_ema_val;
            
            // Kẹp đạo hàm dT tránh bùng nổ chỉ số
            if (dT > DS18B20_MAX_DT) dT = DS18B20_MAX_DT;
            if (dT < -DS18B20_MAX_DT) dT = -DS18B20_MAX_DT;
            
            // Nhiệt độ da sau khi chống trễ cảm biến
            float skin_predict = smooth_val + (dT * DS18B20_PREDICT_TAU);
            
            // === EXTRAPOLATION PREDICTION ===
            thermal_predictor_feed(&tp->predictor, skin_predict, xTaskGetTickCount());
            float t_skin_effective = thermal_predictor_get(&tp->predictor, skin_predict);
            
            // === DUAL-SENSOR COMPENSATION (thay vì room_temp_locked) ===
            float body_val;
            body_temp_quality_t bq = compute_body_temp(t_skin_effective, corrected_ambient,
                                                        humidity, &body_val);
            
            if (bq == BODY_TEMP_ERROR) {
                tp->confidence = 0;
                break; // Lỗi cứng, không cập nhật gì thêm
            }
            
            // Cả VALID lẫn CONVERGING đều được cho qua cổng ổn định
            float final_val;
            temp_stability_t st_state = check_stability(tp, body_val, &final_val);
            tp->current_body_temp = final_val;

            // Tính confidence score
            tp->confidence = compute_confidence(mq, st_state,
                                                 tp->dht11_bias_correction, bq, &tp->predictor);

            // Structured log cho debug (Cải tiến C)
            ESP_LOGV(TAG,
                "skin_pred=%.2f skin_eff=%.2f ambient_dht=%.2f bias=%.3f "
                "k_dyn=%.3f hum=%d t_core=%.2f mq=%d conf=%d",
                skin_predict, t_skin_effective, ambient_temp_dht11,
                tp->dht11_bias_correction,
                compute_k_dynamic(humidity, corrected_ambient),
                humidity, final_val, mq, tp->confidence);
            break;
            
        case THERMAL_STATE_COOLDOWN:
            tp->current_body_temp = 0.0f; // Tắt hiển thị cơ thể
            tp->confidence = 0;
            
            // Giảm timeout hoặc kiểm tra xem cảm biến đã hạ xuống bằng nhiệt phòng chưa
            tp->cooldown_timer--;
            if (tp->cooldown_timer <= 0 || fabsf(smooth_val - tp->room_temp_locked) < 0.5f) {
                tp->state = THERMAL_STATE_IDLE;
            } else if (is_user_present) {
                // Người dùng bất ngờ đặt tay lại
                tp->state = THERMAL_STATE_ACTIVE;
                on_touch_detected(tp, corrected_ambient);
            }
            break;
    }
}

float thermal_processor_get_body_temp(thermal_processor_t *tp) {
    return tp->current_body_temp;
}

float thermal_processor_get_room_temp(thermal_processor_t *tp) {
    return tp->current_room_temp;
}

uint8_t thermal_processor_get_confidence(thermal_processor_t *tp) {
    return tp->confidence;
}

float thermal_processor_get_bias(thermal_processor_t *tp) {
    return tp->dht11_bias_correction;
}
