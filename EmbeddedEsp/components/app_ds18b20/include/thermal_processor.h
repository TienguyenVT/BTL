/**
 * @file thermal_processor.h
 * @brief Module xử lý nhiệt độ DS18B20 áp dụng Median, Kalman, Adaptive EMA và Mô hình truyền nhiệt.
 */
#pragma once

#include <stdbool.h>

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

// 5. MÔ HÌNH BÙ NHIỆT ĐỘNG (THERMAL COMPENSATION)
// k = (T_body_ref - T_skin) / (T_skin - T_room)
#define THERMAL_K_COEFF         0.40f  // Hệ số truyền nhiệt giữa ngón tay và môi trường
#define BODY_TEMP_MIN           34.0f  // Ngưỡng dưới hợp lệ
#define BODY_TEMP_MAX           42.0f  // Ngưỡng trên hợp lệ

// 6. CỔNG ỔN ĐỊNH (STABILITY GATE)
#define STABLE_THRESHOLD        0.1f   // °C sai lệch tối đa để coi là đang hội tụ
#define STABLE_COUNT_REQ        5      // Số chu kỳ liên tiếp cần

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
    float current_room_temp;// Nhiệt độ phòng hện tại
} thermal_processor_t;

// API
void thermal_processor_init(thermal_processor_t *tp);
void thermal_processor_update(thermal_processor_t *tp, float raw_temp, bool is_user_present);

float thermal_processor_get_body_temp(thermal_processor_t *tp);
float thermal_processor_get_room_temp(thermal_processor_t *tp);
