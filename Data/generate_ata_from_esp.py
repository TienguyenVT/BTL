import pandas as pd
import numpy as np
import random
import uuid
from datetime import datetime, timedelta


# ============================================================================
# CẤU HÌNH USER - MÔ PHỎNG DATA THỰC TẾ TỪ ESP
# ============================================================================
# Mỗi user đo trong 1 ngày khác nhau
# User A: ngày 2026-03-14
# User B: ngày 2026-03-15
# User C: ngày 2026-03-16
#
# VỀ GSR_ADC - CĂN CỨ SINH HỌC:
#   GSR (Galvanic Skin Response) đo điện trở/độ dẫn điện của da.
#   Giá trị phụ thuộc vào:
#     - Điện trở da người (người A có thể da dày hơn → trở cao hơn)
#     - Mật độ tuyến mồ hôi (người B/C có thể nhạy cảm hơn → mồ hôi nhiều → trở thấp hơn)
#     - Tình trạng da và tuổi tác
#   => 3 người khác nhau sẽ có baseline GSR khác nhau.
#
# Baseline GSR Normal (không stress, không sốt):
#   - User A: ~2100 (da khô hơn, điện trở da cao)
#   - User B: ~2500 (da ẩm hơn mức trung bình)
#   - User C: ~2350 (giữa A và B)
#
# Mức chênh lệch: User A vs User C chênh ~250 đơn vị ADC (hợp lý về mặt sinh học,
# trong khi phạm vi toàn bộ là 0-4095)
# ============================================================================

USERS = [
    {
        'id': 'User_A',
        'date': '2026-03-14',
        'temp_range': (18, 26),
        'humid_range': (70, 85),
        'gsr_normal_baseline': 2100,  # Da khô hơn
    },
    {
        'id': 'User_B',
        'date': '2026-03-15',
        'temp_range': (20, 28),
        'humid_range': (65, 80),
        'gsr_normal_baseline': 2500,  # Da ẩm hơn, mồ hôi nhiều hơn
    },
    {
        'id': 'User_C',
        'date': '2026-03-16',
        'temp_range': (16, 24),
        'humid_range': (72, 88),
        'gsr_normal_baseline': 2350,  # Trung bình giữa A và B
    },
]

# Time Slots (Approximate start times)
TIME_SLOTS = {
    'Morning': (6, 7),
    'Noon': (11, 12),
    'Afternoon': (14, 15),
    'Evening': (19, 20),
}

SAMPLES_PER_SLOT = 300
INTERVAL_SEC = 3  # ESP đo nhanh hơn, mỗi 3 giây

# ============================================================================
# CĂN CỨ SINH HỌC CHO CÁC THÔNG SỐ
# ============================================================================
# BPM (Nhịp tim):
#   - Normal: 60-90 bpm (nghỉ ngơi), 90-130 (vận động nhẹ)
#   - Stress: 90-160 bpm (do catecholamine tăng)
#   - Fever: 80-110 bpm (tăng ~10-20 bpm / độ sốt)
#
# SpO2 (Nồng độ oxy):
#   - Normal: 96-99%
#   - Stress: thường không giảm nhiều (95-99%)
#   - Fever: có thể giảm nhẹ nếu sốt cao (94-99%)
#
# Body_Temp:
#   - Normal: 36.5-37.2°C
#   - Stress: 36.5-37.5°C (tăng nhẹ do cortisol)
#   - Fever: 37.5-40.0°C
#
# GSR (Electrodermal Activity):
#   - Điện trở da giảm khi mồ hôi tăng (stress/sốt)
#   - Normal: baseline theo từng user (A: 2100, B: 2500, C: 2350)
#   - Stress: tăng mạnh do mồ hôi tăng (A: +600-1200, B: +700-1300, C: +650-1250)
#   - Fever: tăng vừa phải (A: +200-500, B: +250-550, C: +220-520)
# ============================================================================

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))


def inject_noise(value, noise_prob=0.05, max_val=4095):
    """
    Mô phỏng lỗi phần cứng/nhiễu tín hiệu thực tế từ ESP.
    - drop: mất tín hiệu → 0
    - spike: xung nhiễu cao
    - drift: trôi offset
    - outlier: giá trị bất thường nhưng vẫn trong phạm vi đo
    """
    if random.random() < noise_prob:
        noise_type = random.choice(['drop', 'spike', 'drift', 'outlier'])
        if noise_type == 'drop':
            return 0
        elif noise_type == 'spike':
            return max_val
        elif noise_type == 'drift':
            return value + random.uniform(-80, 80)
        elif noise_type == 'outlier':
            return value * random.choice([0.4, 0.6, 1.4, 1.6])
    return value


def generate_esp_data(user_config):
    """
    Sinh dữ liệu mô phỏng data thực tế từ ESP32-S3.
    KHÔNG có cột Label - data thô từ cảm biến.
    """
    user_id = user_config['id']
    base_date = datetime.strptime(user_config['date'], '%Y-%m-%d')
    weather_temp_min, weather_temp_max = user_config['temp_range']
    weather_humid_min, weather_humid_max = user_config['humid_range']
    gsr_baseline = user_config['gsr_normal_baseline']

    data = []

    # Trạng thái sinh lý hiện tại
    current_bpm = 75
    current_spo2 = 98.0
    current_temp = 36.8
    current_gsr = gsr_baseline  # Baseline khác nhau cho mỗi user
    current_state = 'Normal'
    state_duration = 0

    # Trạng thái thời tiết
    current_ext_temp = (weather_temp_min + weather_temp_max) / 2
    current_ext_humid = (weather_humid_min + weather_humid_max) / 2

    # Đếm mẫu cho mỗi slot
    base_per_slot = SAMPLES_PER_SLOT
    remainder = random.randint(0, 3)  # Thêm chút ngẫu nhiên

    # =========================================================================
    # SINH DỮ LIỆU THEO TIME SLOTS
    # =========================================================================
    for idx, (slot_name, (start_hour_min, start_hour_max)) in enumerate(TIME_SLOTS.items()):
        slot_samples = base_per_slot + (1 if idx < remainder else 0)

        # Random thời điểm bắt đầu trong khung giờ
        start_hour = random.randint(start_hour_min, start_hour_max)
        start_minute = random.randint(0, 59)
        start_second = random.randint(0, 59)
        start_time = base_date.replace(hour=start_hour, minute=start_minute, second=start_second)

        # Điều chỉnh thời tiết theo thời điểm trong ngày
        if slot_name in ['Morning', 'Evening']:
            ext_temp_bias = -2.5
            ext_humid_bias = 8.0
        elif slot_name == 'Noon':
            ext_temp_bias = 3.0
            ext_humid_bias = -8.0
        else:  # Afternoon
            ext_temp_bias = 1.0
            ext_humid_bias = -3.0

        current_ext_temp = clamp(current_ext_temp + ext_temp_bias, weather_temp_min - 3, weather_temp_max + 3)
        current_ext_humid = clamp(current_ext_humid + ext_humid_bias, weather_humid_min - 8, weather_humid_max + 8)

        # =========================================================================
        # SINH TỪNG MẪU DỮ LIỆU
        # =========================================================================
        for i in range(slot_samples):
            timestamp = start_time + timedelta(seconds=i * INTERVAL_SEC)

            # --- Chuyển trạng thái sinh lý ---
            if state_duration <= 0:
                # Xác suất các trạng thái
                current_state = random.choices(
                    ['Normal', 'Stress', 'Fever'],
                    weights=[0.55, 0.30, 0.15]
                )[0]
                # Thời gian ở mỗi trạng thái (số mẫu)
                if current_state == 'Normal':
                    state_duration = random.randint(40, 100)
                elif current_state == 'Stress':
                    state_duration = random.randint(25, 60)
                else:  # Fever
                    state_duration = random.randint(50, 120)
            else:
                state_duration -= 1

            # --- Cập nhật các chỉ số sinh lý theo trạng thái ---
            if current_state == 'Normal':
                # Trở về baseline của từng user
                current_bpm += random.uniform(-2.5, 2.5) + (75 - current_bpm) * 0.08
                current_bpm = clamp(current_bpm, 58, 88)

                current_spo2 += random.uniform(-0.4, 0.4)
                current_spo2 = clamp(current_spo2, 96.0, 99.9)

                current_temp += random.uniform(-0.08, 0.08) + (36.8 - current_temp) * 0.15
                current_temp = clamp(current_temp, 36.5, 37.1)

                # GSR về baseline của user đó
                gsr_target = gsr_baseline + random.uniform(-50, 50)
                current_gsr += random.uniform(-25, 25) + (gsr_target - current_gsr) * 0.12
                current_gsr = clamp(current_gsr, gsr_baseline - 200, gsr_baseline + 200)

            elif current_state == 'Stress':
                # Gọi thêm catecholamine → nhịp tim tăng, mồ hôi tăng → GSR tăng
                current_bpm += random.uniform(0, 6)
                current_bpm = clamp(current_bpm, 95, 160)

                current_spo2 += random.uniform(-0.3, 0.3)
                current_spo2 = clamp(current_spo2, 96.0, 99.9)

                current_temp += random.uniform(-0.05, 0.1) + (36.9 - current_temp) * 0.1
                current_temp = clamp(current_temp, 36.5, 37.4)

                # GSR tăng đáng kể do mồ hôi tăng mạnh
                # Baseline khác nhau → mức tăng GSR khác nhau (mồ hôi tuyệt đối khác nhau)
                gsr_stress_min = gsr_baseline + 550
                gsr_stress_max = gsr_baseline + 1300
                current_gsr += random.uniform(15, 55)
                current_gsr = clamp(current_gsr, gsr_stress_min, min(gsr_stress_max, 4095))

            elif current_state == 'Fever':
                # Cơ thể phản ứng với sốt → nhịp tim tăng, GSR tăng vừa phải
                current_bpm += random.uniform(-1, 3)
                current_bpm = clamp(current_bpm, 85, 115)

                current_spo2 += random.uniform(-0.5, 0.3)
                current_spo2 = clamp(current_spo2, 94.0, 99.5)

                # Nhiệt độ tăng dần khi sốt
                current_temp += random.uniform(-0.03, 0.12)
                current_temp = clamp(current_temp, 37.5, 40.0)

                # GSR tăng vừa phải do mồ hôi (không mạnh như stress cấp)
                gsr_fever_min = gsr_baseline + 180
                gsr_fever_max = gsr_baseline + 520
                current_gsr += random.uniform(-10, 30)
                current_gsr = clamp(current_gsr, gsr_fever_min, gsr_fever_max)

            # --- Cập nhật thời tiết (random walk) ---
            current_ext_temp += random.uniform(-0.06, 0.06)
            current_ext_temp = clamp(current_ext_temp, weather_temp_min - 5, weather_temp_max + 5)

            current_ext_humid += random.uniform(-0.15, 0.15)
            current_ext_humid = clamp(current_ext_humid, weather_humid_min - 12, weather_humid_max + 12)

            # --- Tạo mẫu dữ liệu cuối cùng ---
            final_bpm = int(clamp(current_bpm, 40, 200))
            final_spo2 = int(clamp(current_spo2, 85.0, 100.0))
            final_temp = round(clamp(current_temp, 35.0, 42.0), 2)
            final_gsr = int(clamp(current_gsr, 0, 4095))
            final_confidence = 100

            # --- Inject noise (lỗi phần cứng ESP - khoảng 8%) ---
            if random.random() < 0.08:
                final_confidence = random.choice([0, 50])
                noise_targets = random.sample(['bpm', 'spo2', 'temp', 'gsr'], k=random.randint(1, 2))
                if 'bpm' in noise_targets:
                    final_bpm = inject_noise(final_bpm, noise_prob=1.0, max_val=255)
                    final_bpm = int(clamp(final_bpm, 0, 255))
                if 'spo2' in noise_targets:
                    final_spo2 = int(inject_noise(final_spo2, noise_prob=1.0, max_val=100))
                    final_spo2 = int(clamp(final_spo2, 0, 100))
                if 'temp' in noise_targets:
                    final_temp = inject_noise(final_temp, noise_prob=1.0, max_val=45.0)
                    final_temp = round(clamp(final_temp, 0.0, 50.0), 2)
                if 'gsr' in noise_targets:
                    final_gsr = inject_noise(final_gsr, noise_prob=1.0, max_val=4095)
                    final_gsr = int(clamp(final_gsr, 0, 4095))

            # --- Engineered Features ---
            eps = 1e-6
            bpm_spo2_ratio = final_bpm / (final_spo2 + eps)
            temp_gsr_interaction = (final_temp * final_gsr) / 1000.0
            bpm_temp_product = final_bpm * final_temp
            spo2_gsr_ratio = final_spo2 / (final_gsr + eps)
            bpm_deviation = abs(final_bpm - 75)
            temp_deviation = abs(final_temp - 36.8)
            gsr_deviation = abs(final_gsr - 2200)
            physiological_stress_index = (final_bpm - 75) / 75.0 + (final_gsr - 2200) / 2200.0

            predicted_label = current_state
            
            # Simulated PPG confidence probability
            esp_confidence = final_confidence / 100.0  # ESP32's confidence field (PPG quality)
            if final_confidence == 100:
                probability = round(random.uniform(0.70, 0.99), 4)  # ML prediction confidence
            else:
                probability = round(random.uniform(0.20, 0.60), 4)  # ML prediction confidence

            ingested_at = (timestamp + timedelta(milliseconds=random.randint(200, 1500))).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "+00:00"
            _id_hex = uuid.uuid4().hex[:24]

            device_id_map = {
                'User_A': 'esp32_iot_health_01',
                'User_B': 'esp32_iot_health_02',
                'User_C': 'esp32_iot_health_03'
            }

            data.append({
                '_id': _id_hex,
                'device_id': device_id_map.get(user_id, 'esp32_iot_health_00'),
                'timestamp': int(timestamp.timestamp()),
                'bpm': final_bpm,
                'spo2': final_spo2,
                'body_temp': final_temp,
                'gsr_adc': final_gsr,
                'mode': 2,
                'dht11_room_temp': round(current_ext_temp, 2),
                'dht11_humidity': round(current_ext_humid, 1),
                'confidence': esp_confidence,
                'dht11_bias': round(random.uniform(-0.5, 0.5), 2),
                'bpm_spo2_ratio': bpm_spo2_ratio,
                'temp_gsr_interaction': temp_gsr_interaction,
                'bpm_temp_product': bpm_temp_product,
                'spo2_gsr_ratio': spo2_gsr_ratio,
                'bpm_deviation': bpm_deviation,
                'temp_deviation': temp_deviation,
                'gsr_deviation': gsr_deviation,
                'physiological_stress_index': physiological_stress_index,
                'predicted_label': predicted_label,
                'confidence': probability,
                'ingested_at': ingested_at
            })

    return pd.DataFrame(data)


if __name__ == "__main__":
    all_dfs = []

    for user_config in USERS:
        df = generate_esp_data(user_config)
        all_dfs.append(df)
        print(f"[{user_config['id']}] Generated {len(df)} rows for {user_config['date']} "
              f"(GSR baseline: {user_config['gsr_normal_baseline']})")

    # Ghép tất cả user vào 1 file
    final_df = pd.concat(all_dfs, ignore_index=True)

    # Lưu file JSON để dễ đẩy vào MongoDB
    filename = "health_data_from_esp.json"
    final_df.to_json(filename, orient='records', lines=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Generated: {filename}")
    print(f"Total rows: {len(final_df)}")
    print(f"Users: {', '.join([u['id'] for u in USERS])}")
    print(f"Columns: {list(final_df.columns)}")
    print(f"{'='*60}")

    # Thống kê GSR
    print("\n--- GSR Statistics (per Device) ---")
    for device_id in final_df['device_id'].unique():
        device_df = final_df[final_df['device_id'] == device_id]
        gsr = device_df['gsr_adc']
        print(f"  {device_id}: min={gsr.min()}, max={gsr.max()}, "
              f"mean={gsr.mean():.1f}, median={gsr.median():.1f}")
