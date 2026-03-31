/**
 * @file thermal_processor.h
 * @brief Module xử lý nhiệt độ DS18B20 áp dụng Median, Kalman, Adaptive EMA và Mô hình truyền nhiệt.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

// --- CẤU HÌNH THAM SỐ THUẬT TOÁN ---

// 1. BỘ LỌC MEDIAN
#define MEDIAN_WINDOW_SIZE      5

// 2. BỘ LỌC KALMAN 1D
#define KALMAN_Q                0.05f  // Nhiễu quá trình (mức độ nhiệt độ biến thiên)
#define KALMAN_R                1.0f   // Nhiễu đo lường (độ không tin cậy của DS18B20)

// 3. BỘ LỌC ADAPTIVE EMA
#define EMA_ALPHA_FAST          0.30f  // Phản ứng nhanh khi nhiệt thay đổi
#define EMA_ALPHA_SLOW          0.05f  // Lọc mịn khi ổn định
#define EMA_CHANGE_THRESHOLD    0.3f   // °C sai lệch giữa 2 chu kỳ để kích hoạt ALPHA_FAST

// 4. BÙ ĐẮP ĐỘ TRỄ (PREDICTIVE ASYMPTOTIC)
#define DS18B20_PREDICT_TAU     2.0f   // Hệ số nhân đạo hàm
#define DS18B20_MAX_DT          0.5f   // Kẹp đạo hàm lớn nhất trong 1 chu kỳ để tránh spike

// 5. MÔ HÌNH BÙ NHIỆT ĐỘNG (DUAL-SENSOR COMPENSATION)
#define THERMAL_K_BASE            0.40f  // Hệ số truyền nhiệt cơ bản
#define HUMIDITY_K_SENSITIVITY    0.003f // Độ nhạy k theo humidity
#define VASOCONSTRICTION_THRESHOLD 22.0f // °C — dưới ngưỡng này co mạch tăng
#define VASOCONSTRICTION_FACTOR   0.008f // k tăng thêm per °C dưới ngưỡng
#define BODY_TEMP_MIN           34.0f  // Ngưỡng dưới hợp lệ
#define BODY_TEMP_MAX           42.0f  // Ngưỡng trên hợp lệ

// 6. CỔNG KIỂM TRA SINH LÝ (PHYSIOLOGICAL GATE)
#define T_SKIN_MIN_VALID        28.0f  // °C — dưới mức này: chạm chưa đủ
#define T_SKIN_MAX_VALID        40.0f  // °C — trên mức này: bất thường
#define SKIN_STABILITY_RATE     0.15f  // °C/s — T_skin phải ổn định

// 7. CỔNG ỔN ĐỊNH (STABILITY GATE)
#define STABLE_THRESHOLD        0.1f   // °C sai lệch tối đa để coi là đang hội tụ
#define STABLE_COUNT_REQ        5      // Số chu kỳ liên tiếp cần

// 8. SENSOR FUSION BIAS CORRECTION (DHT11 ↔ DS18B20)
#define BIAS_CORRECTION_ALPHA   0.005f // Tốc độ học bias (rất chậm)
#define MAX_SENSOR_DIVERGENCE   3.0f   // °C — nếu > 3°C thì cảnh báo
#define DHT11_AMBIENT_EMA_ALPHA 0.2f   // EMA alpha cho ambient temp từ DHT11

// 9. WARM START (Rút ngắn thời gian hội tụ Kalman)
#define WARM_START_OFFSET      7.0f    // T_ambient + 7 = prior T_skin ban đầu
#define WARM_START_VARIANCE    16.0f   // 4°C std dev — uncertainty cao, Kalman tin measurement

// 10. EXPONENTIAL EXTRAPOLATION (T_inf PREDICTION)
#define PRED_BUF_SIZE     12
#define PRED_SAMPLE_MS    4000     // lấy mẫu mỗi 4 giây — đủ thưa để thấy curve
#define PRED_MIN_POINTS   6        // cần ít nhất 6 điểm trước khi predict
#define PRED_STABLE_ERR   0.25f    // °C — nếu T_inf thay đổi < 0.25°C qua 3 lần → ổn định
#define PRED_PHY_MIN      33.0f
#define PRED_PHY_MAX      38.5f

// --- CẤU TRÚC DỮ LIỆU ---

typedef enum {
    THERMAL_STATE_IDLE,     // Không có người dùng
    THERMAL_STATE_ACTIVE,   // Người dùng đang chạm ngón tay
    THERMAL_STATE_COOLDOWN  // Người dùng vừa thả tay, chờ cảm biến nguội
} thermal_state_t;

typedef struct {
    float x; // Ước lượng trạng thái hiện tại
    float P; // Hiệp phương sai sai số
    float Q; // Nhiễu quá trình setup
    float R; // Nhiễu đo lường setup
} kalman_filter_t;

typedef struct {
    float   temps[PRED_BUF_SIZE];
    uint32_t ticks[PRED_BUF_SIZE];
    int     count;
    int     head;

    float   t_inf_history[3];     // 3 lần predict gần nhất để check stability
    int     hist_idx;

    float   t_inf_stable;         // kết quả cuối khi đã ổn định
    bool    is_stable;
    uint32_t last_sample_tick;
} thermal_predictor_t;

typedef struct {
    // Pipeline Tầng 1: Median
    float median_buf[MEDIAN_WINDOW_SIZE];
    int median_idx;
    bool median_filled;

    // Pipeline Tầng 2: Kalman
    kalman_filter_t kalman;

    // Pipeline Tầng 3: Adaptive EMA
    float ema_val;
    float prev_ema_val; // Chuyên dùng cho tính đạo hàm (dT)
    bool ema_initialized;

    // Pipeline Tầng 4: State Machine
    thermal_state_t state;
    int cooldown_timer; // Số chu kỳ đếm ngược trong COOLDOWN

    // Pipeline Tầng 5: Độ Ổn Định
    float last_stable;
    int stable_count;
    bool is_stable;

    // Dữ liệu bộ lọc & chốt
    float room_temp_locked; // Khóa giá trị phòng ngay trước khi chạm 
    float current_body_temp;// Nhiệt độ cơ thể hợp lệ cuối cùng
    float current_room_temp;// Nhiệt độ phòng hiện tại (DS18B20 IDLE)

    // Dual-sensor fusion
    float dht11_bias_correction; // Learned bias correction cho DHT11
    float prev_skin_temp;   // T_skin chu kỳ trước (tính dT/dt)
    uint8_t confidence;     // 0-100 measurement confidence

    // Warm start & Extrapolation
    thermal_predictor_t predictor;
    uint32_t touch_start_tick;
    bool prediction_ready;
} thermal_processor_t;

// API
void thermal_processor_init(thermal_processor_t *tp);
void thermal_processor_update(thermal_processor_t *tp, float raw_temp, bool is_user_present,
                              float ambient_temp_dht11, int humidity);

float thermal_processor_get_body_temp(thermal_processor_t *tp);
float thermal_processor_get_room_temp(thermal_processor_t *tp);
uint8_t thermal_processor_get_confidence(thermal_processor_t *tp);
float thermal_processor_get_bias(thermal_processor_t *tp);
