import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# User Configuration
USERS = [
    {'id': 'User1', 'date': '2026-02-26', 'temp_range': (15, 25), 'humid_range': (75, 80)},
    {'id': 'User1', 'date': '2026-02-28', 'temp_range': (14, 20), 'humid_range': (75, 85)},
    {'id': 'User1', 'date': '2026-03-03', 'temp_range': (14, 20), 'humid_range': (70, 85)},
    {'id': 'User1', 'date': '2026-03-06', 'temp_range': (19, 22), 'humid_range': (80, 90)},
    {'id': 'User1', 'date': '2026-03-11', 'temp_range': (14, 19), 'humid_range': (70, 80)},
]

# Time Slots (Approximate start times)
TIME_SLOTS = {
    'Morning': (5, 6),      # 5:00 - 6:59 start
    'Noon': (11, 12),       # 11:00 - 12:59 start
    'Afternoon': (15, 16),  # 15:00 - 16:59 start
    'Night': (22, 23)       # 22:00 - 23:59 start
}

SAMPLES_PER_SLOT = 250 # Total ~1000 rows
INTERVAL_SEC = 5

# Range Constraints (Bio)
BPM_RANGE = (60, 180)
SPO2_RANGE = (85, 100)
TEMP_RANGE = (36.0, 40.0)
GSR_RANGE = (0, 4095)

# Scenarios - Cân bằng class distribution hơn
# Trước: [0.7, 0.2, 0.1] → quá imbalance (70% Normal)
# Sau: [0.5, 0.3, 0.2] → cân bằng hơn
SCENARIOS = ['Normal', 'Stress', 'Fever']
SCENARIO_WEIGHTS = [0.5, 0.3, 0.2]

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

def inject_noise(value, noise_prob=0.05, min_val=0, max_val=4095):
    """Randomly inject noise: 0, negative, max value, random outlier, or drift."""
    if random.random() < noise_prob:
        noise_type = random.choice(['drop', 'negative', 'max', 'outlier', 'drift'])
        if noise_type == 'drop': 
            return 0
        elif noise_type == 'negative': 
            return -random.randint(1, 100)
        elif noise_type == 'max': 
            return max_val
        elif noise_type == 'outlier':
            # Generate a value significantly outside normal range but possibly valid type
            # e.g., 200% of value or 50%
            return value * random.choice([0.5, 2.0]) 
        elif noise_type == 'drift':
             # Add significant random offset
             return value + random.uniform(-50, 50)
    return value

def generate_user_data(user_config):
    user_id = user_config['id']
    base_date = datetime.strptime(user_config['date'], '%Y-%m-%d')
    weather_temp_min, weather_temp_max = user_config['temp_range']
    weather_humid_min, weather_humid_max = user_config['humid_range']
    
    data = []
    
    # Bio state initialization
    current_bpm = 75
    current_spo2 = 98.0
    current_temp = 36.8
    current_gsr = 2200
    current_state = 'Normal'
    state_duration = 0
    
    # Weather state initialization
    current_ext_temp = (weather_temp_min + weather_temp_max) / 2
    current_ext_humid = (weather_humid_min + weather_humid_max) / 2
    
    # Calculate total samples for this user day (approx 2000 to get ~10000 for 5 days)
    total_log_count = random.randint(1950, 2050)
    # Distribute mostly evenly across 4 slots, with slight randomness
    base_per_slot = total_log_count // 4
    remainder = total_log_count % 4
    
    # Loop through time slots
    slot_names = list(TIME_SLOTS.keys())
    for idx, (slot_name, (start_hour_min, start_hour_max)) in enumerate(TIME_SLOTS.items()):
        # Determine count for this slot
        slot_samples = base_per_slot + (1 if idx < remainder else 0)
        
        # Randomize start time within the slot hour range
        start_hour = random.randint(start_hour_min, start_hour_max)
        start_minute = random.randint(0, 59)
        start_time = base_date.replace(hour=start_hour, minute=start_minute, second=0)
        
        # Adjust weather baseline based on time of day
        # Morning/Night: cooler, higher humidity?
        # Noon/Afternoon: warmer, lower humidity?
        slot_temp_bias = 0
        slot_humid_bias = 0
        
        if slot_name in ['Morning', 'Night']:
             slot_temp_bias = -2.0
             slot_humid_bias = 5.0
        else: # Noon, Afternoon
             slot_temp_bias = 2.0
             slot_humid_bias = -5.0
             
        # Apply bias but stay within reasonable physics of the day
        current_ext_temp = clamp(current_ext_temp + slot_temp_bias, weather_temp_min - 2, weather_temp_max + 2)
        current_ext_humid = clamp(current_ext_humid + slot_humid_bias, weather_humid_min - 5, weather_humid_max + 5)

        for i in range(slot_samples):
            timestamp = start_time + timedelta(seconds=i*INTERVAL_SEC)
            
            # --- State Transition Logic ---
            if state_duration <= 0:
                current_state = random.choices(SCENARIOS, weights=SCENARIO_WEIGHTS)[0]
                state_duration = random.randint(20, 60)
            else:
                state_duration -= 1
            
            # --- Bio Logic ---
            # (Same as before)
            if current_state == 'Normal':
                current_bpm += random.uniform(-2, 2) + (75 - current_bpm) * 0.1
                current_bpm = clamp(current_bpm, 60, 90)
                current_spo2 += random.uniform(-0.5, 0.5)
                current_spo2 = clamp(current_spo2, 96, 99.9)
                current_temp += random.uniform(-0.1, 0.1) + (36.8 - current_temp) * 0.2
                current_temp = clamp(current_temp, 36.5, 37.2)
                current_gsr += random.uniform(-20, 20) + (2200 - current_gsr) * 0.1
                current_gsr = clamp(current_gsr, 2100, 2300)

            elif current_state == 'Stress':
                current_bpm += random.uniform(0, 5)
                current_bpm = clamp(current_bpm, 100, 160)
                current_spo2 += random.uniform(-0.5, 0.5)
                current_spo2 = clamp(current_spo2, 96, 99.9) # SpO2 usually normal in stress
                current_temp += random.uniform(-0.1, 0.1) + (36.8 - current_temp) * 0.2
                current_temp = clamp(current_temp, 36.5, 37.5) # Slight rise maybe?
                current_gsr += random.uniform(10, 50)
                current_gsr = clamp(current_gsr, 2600, 4000)

            elif current_state == 'Fever':
                current_bpm += random.uniform(-1, 2)
                current_bpm = clamp(current_bpm, 80, 110)
                current_spo2 += random.uniform(-0.5, 0.5)
                current_spo2 = clamp(current_spo2, 94, 99)
                current_temp += random.uniform(-0.05, 0.15)
                current_temp = clamp(current_temp, 37.6, 40.0)
                current_gsr = clamp(current_gsr, 2000, 2500) # Normal-ish GSR

            # --- Weather Logic (Random Walk) ---
            current_ext_temp += random.uniform(-0.05, 0.05)
            current_ext_temp = clamp(current_ext_temp, weather_temp_min - 5, weather_temp_max + 5)
            
            current_ext_humid += random.uniform(-0.1, 0.1)
            current_ext_humid = clamp(current_ext_humid, weather_humid_min - 10, weather_humid_max + 10)

            # --- Noise Injection (10% overall error rate) ---
            # FIX: Khi inject noise, label PHẢI là 'Error' để tránh label mismatch
            # Trước đây có bug: 50% giữ nguyên label nhưng features đã bị corrupt
            final_bpm = int(current_bpm)
            final_spo2 = round(current_spo2, 1)
            final_temp = round(current_temp, 2)
            final_gsr = int(current_gsr)

            final_label = current_state

            if random.random() < 0.10:
                # Khi có noise → label phải là 'Error' (không giữ nguyên label sinh lý)
                final_label = 'Error'

                noise_targets = random.sample(['bpm', 'spo2', 'temp', 'gsr'], k=random.randint(1, 2))
                if 'bpm' in noise_targets: final_bpm = inject_noise(final_bpm, noise_prob=1.0, max_val=255)
                if 'spo2' in noise_targets: final_spo2 = inject_noise(final_spo2, noise_prob=1.0, max_val=100)
                if 'temp' in noise_targets: final_temp = inject_noise(final_temp, noise_prob=1.0, max_val=45.0)
                if 'gsr' in noise_targets: final_gsr = inject_noise(final_gsr, noise_prob=1.0, max_val=4095)

            data.append({
                'User_ID': user_id,
                'Timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Time_Slot': slot_name,
                'BPM': final_bpm,
                'SpO2': final_spo2,
                'Body_Temp': final_temp,
                'GSR_ADC': final_gsr,
                'Ext_Temp_C': round(current_ext_temp, 1),
                'Ext_Humidity_Pct': round(current_ext_humid, 1),
                'Label': final_label
            })
            
    return pd.DataFrame(data)

if __name__ == "__main__":
    all_dfs = []
    for user_config in USERS:
        df = generate_user_data(user_config)
        all_dfs.append(df)
        print(f"Generated {len(df)} rows for date {user_config['date']}.")
        
    final_df = pd.concat(all_dfs, ignore_index=True)
    filename = "health_data_all.csv"
    final_df.to_csv(filename, index=False)
    print(f"Successfully generated {filename} with a total of {len(final_df)} rows.")
