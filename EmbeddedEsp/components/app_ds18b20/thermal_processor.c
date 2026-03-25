#include "thermal_processor.h"
#include <string.h>
#include <math.h>

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
    float alpha = (rate > EMA_CHANGE_THRESHOLD) ? EMA_ALPHA_FAST : EMA_ALPHA_SLOW;
    tp->ema_val = alpha * new_sample + (1.0f - alpha) * tp->ema_val;
    
    return tp->ema_val;
}

typedef enum {
    BODY_TEMP_VALID,       // ổn định, trong ngưỡng sinh lý
    BODY_TEMP_CONVERGING,  // đang hội tụ, chưa đáng tin hoàn toàn
    BODY_TEMP_ERROR        // thực sự lỗi (âm, > 45°C, sensor rời tay)
} body_temp_quality_t;

static body_temp_quality_t compute_body_temp(float t_skin, float t_room, float *out_compensated) {
    if (t_skin < 20.0f || t_skin > 45.0f) {
        *out_compensated = 0.0f;
        return BODY_TEMP_ERROR;
    }

    float compensated;
    if (t_room < 10.0f || t_room > 40.0f) {
        // Fallback offset cố định nếu nhiệt độ phòng không hợp lệ
        compensated = (t_skin > 30.0f) ? t_skin + 4.5f : t_skin;
    } else {
        // k = (T_body_ref - T_skin) / (T_skin - T_room)
        compensated = t_skin + THERMAL_K_COEFF * (t_skin - t_room);
    }
    
    *out_compensated = compensated;

    if (compensated >= BODY_TEMP_MIN && compensated <= BODY_TEMP_MAX) {
        return BODY_TEMP_VALID; // Nằm trong khoảng hợp lý của cơ thể
    } else if (compensated >= 28.0f && compensated < BODY_TEMP_MIN) {
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

// =========================================================
// HÀM XỬ LÝ CHÍNH ĐƯỢC GỌI MỖI CHU KỲ BỞI TASK
// =========================================================
void thermal_processor_update(thermal_processor_t *tp, float raw_temp, bool is_user_present) {
    if (raw_temp <= -100.0f) {
        return; // Lỗi đọc cảm biến I2C/OneWire (dữ liệu rác)
    }

    // 1. Lọc nhiễu tĩnh & động
    float median_val = apply_median_filter(tp, raw_temp);
    float kalman_val = apply_kalman_filter(&tp->kalman, median_val);
    float smooth_val = apply_adaptive_ema(tp, kalman_val);

    // 2. State Machine quản lý chế độ (Phòng / Chạm tay / Nguội dầ)
    switch(tp->state) {
        case THERMAL_STATE_IDLE:
            tp->current_room_temp = smooth_val;
            tp->room_temp_locked = smooth_val; // Chốt môi trường để dành bù nhiệt
            tp->current_body_temp = 0.0f;      // Không đo người
            
            if (is_user_present) {
                // Sang thái ACTIVE: người dùng bắt đầu chạm tay
                tp->state = THERMAL_STATE_ACTIVE;
                tp->stable_count = 0;
                tp->is_stable = false;
            }
            break;
            
        case THERMAL_STATE_ACTIVE:
            if (!is_user_present) {
                // Người dùng nhả tay ngẫu nhiên -> vào trạng thái chờ nguội vãn (hạ nhiệt)
                tp->state = THERMAL_STATE_COOLDOWN;
                tp->cooldown_timer = 120; // Ví dụ 120 chu kỳ (mỗi chu kỳ = 0.5s -> 60 giây)
                tp->current_body_temp = 0.0f; // Tắp thân nhiệt
                break;
            }
            
            // Xử lý bù độ trễ (Asymptotic Prediction)
            float dT = smooth_val - tp->prev_ema_val;
            
            // Kẹp đạo hàm dT tránh bùng nổ chỉ số
            if (dT > DS18B20_MAX_DT) dT = DS18B20_MAX_DT;
            if (dT < -DS18B20_MAX_DT) dT = -DS18B20_MAX_DT;
            
            // Nhiệt độ da sau khi chống trễ cảm biến
            float skin_predict = smooth_val + (dT * DS18B20_PREDICT_TAU);
            
            // Bù nhiễu nhiệt lượng mất đi ra môi trường phòng
            float body_val;
            body_temp_quality_t quality = compute_body_temp(skin_predict, tp->room_temp_locked, &body_val);
            
            if (quality == BODY_TEMP_ERROR) {
                break; // Lỗi cứng, không cập nhật gì thêm
            }
            
            // Cả VALID lẫn CONVERGING đều được cho qua cổng ổn định để UI thấy số đang tịnh tiến
            float final_val;
            temp_stability_t st_state = check_stability(tp, body_val, &final_val);
            tp->current_body_temp = final_val; 
            break;
            
        case THERMAL_STATE_COOLDOWN:
            tp->current_body_temp = 0.0f; // Tắt luôn hiển thị cơ thể
            
            // Không cập nhật room_temp trong lúc này do ngón tay vẫn tỏa hơi nóng làm cảm biến cao
            
            // Giảm timeout hoặc kiểm tra xem cảm biến đã hạ xuống bằng nhiệt phòng chưa
            tp->cooldown_timer--;
            // Sai số 0.5 độ so với lúc khóa thì coi như đã nguội hẳn
            if (tp->cooldown_timer <= 0 || fabsf(smooth_val - tp->room_temp_locked) < 0.5f) {
                tp->state = THERMAL_STATE_IDLE;
            } else if (is_user_present) {
                // Người dùng bất ngờ đặt tay lại
                tp->state = THERMAL_STATE_ACTIVE;
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
