#!/usr/bin/env python3
"""
Script loc du lieu IoMT tu MongoDB va xuat CSV de gan nhan thu cong.
Sau khi sua thuat toan SpO2 tren ESP32, du lieu cu can duoc:
1. Loc theo nguong sinh ly hop ly
2. Gan nhan thu cong dua tren ngu canh
"""

import json
import csv
import os
from datetime import datetime
from collections import Counter

# --- CAU HINH ---
INPUT_FILE = "Data/iomt_health_monitor.realtime_health_data.json"
OUTPUT_FILE = "Data/labeled_data_for_annotation.csv"
OUTPUT_FILTERED = "Data/filtered_data_analysis.csv"

# Nguong filter theo gia tri sinh ly hop ly
# CHU Y: Du lieu cu co body_temp max = 30.8*C (bat thuong)
# -> Tam thoi mo rong nguong de xem xet du lieu
FILTER_THRESHOLDS = {
    "bpm": {"min": 50, "max": 140, "unit": "bpm"},
    "spo2": {"min": 85, "max": 100, "unit": "%"},
    # MO RONG TAM THOI: Du lieu cu co body_temp ~30*C (bat thuong)
    # Sau khi thu thap lai du lieu moi, dat ve 35.0 - 39.5
    "body_temp": {"min": 29.0, "max": 39.5, "unit": "C"},
    "gsr_adc": {"min": 100, "max": 5000, "unit": "ADC"},
}

# Nguong canh bao nghiem ngat (dung de danh dau du lieu co van de)
WARNING_THRESHOLDS = {
    "bpm": {"low": 60, "high": 100},
    "spo2": {"low": 95, "critical": 90},
    "body_temp": {"low": 36.0, "high": 37.5, "fever": 38.0},  # Nguong sinh ly binh thuong
    "gsr_adc": {"low": 1000, "high": 3000},
}

# Nguong filter du lieu " sach " (sau khi thu thap lai voi ESP32 da sua)
CLEAN_THRESHOLDS = {
    "bpm": {"min": 60, "max": 120, "unit": "bpm"},
    "spo2": {"min": 90, "max": 100, "unit": "%"},
    "body_temp": {"min": 35.5, "max": 38.5, "unit": "C"},
    "gsr_adc": {"min": 500, "max": 4000, "unit": "ADC"},
}


def load_data(filepath):
    """Load JSON data from MongoDB export."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Da load {len(data)} records tu {filepath}")
    return data


def suggest_label(record, warning_thresholds):
    """
    De xuat nhan tu dong (chi tham khao, KHONG dung de train model).
    Chi dung cho viec xem truoc, nhan thuc te phai do bac si/expert gan.
    """
    bpm = record.get('bpm', 0)
    spo2 = record.get('spo2', 0)
    body_temp = record.get('body_temp', 0)
    gsr = record.get('gsr_adc', 0)

    issues = []

    if bpm > 0:
        if bpm < warning_thresholds["bpm"]["low"]:
            issues.append("HR_LOW")
        elif bpm > warning_thresholds["bpm"]["high"]:
            issues.append("HR_HIGH")

    if spo2 > 0:
        if spo2 < warning_thresholds["spo2"]["critical"]:
            issues.append("HYPOXIA")
        elif spo2 < warning_thresholds["spo2"]["low"]:
            issues.append("LOW_SPO2")

    if body_temp > 0:
        if body_temp < warning_thresholds["body_temp"]["low"]:
            issues.append("TEMP_LOW")
        elif body_temp >= warning_thresholds["body_temp"]["fever"]:
            issues.append("FEVER")
        elif body_temp > warning_thresholds["body_temp"]["high"]:
            issues.append("TEMP_HIGH")

    if gsr > 0:
        if gsr > warning_thresholds["gsr_adc"]["high"]:
            issues.append("HIGH_STRESS")

    if not issues:
        return "Normal", "All vitals within range"
    else:
        return "Warning", "; ".join(issues)


def check_filters(record, thresholds):
    """Kiem tra xem record co vuot nguong khong."""
    reasons = []

    bpm = record.get('bpm', 0)
    spo2 = record.get('spo2', 0)
    body_temp = record.get('body_temp', 0)
    gsr = record.get('gsr_adc', 0)

    if bpm > 0 and (bpm < thresholds["bpm"]["min"] or bpm > thresholds["bpm"]["max"]):
        reasons.append(f"BPM={bpm} out of range")

    if spo2 > 0 and (spo2 < thresholds["spo2"]["min"] or spo2 > thresholds["spo2"]["max"]):
        reasons.append(f"SpO2={spo2} out of range")

    if body_temp > 0 and (body_temp < thresholds["body_temp"]["min"] or body_temp > thresholds["body_temp"]["max"]):
        reasons.append(f"Temp={body_temp} out of range")

    if gsr > 0 and (gsr < thresholds["gsr_adc"]["min"] or gsr > thresholds["gsr_adc"]["max"]):
        reasons.append(f"GSR={gsr} out of range")

    return reasons


def assess_quality(record, clean_thresholds):
    """Danh gia chat luong du lieu dua tren nguong sach."""
    issues = []
    bpm = record.get('bpm', 0)
    spo2 = record.get('spo2', 0)
    body_temp = record.get('body_temp', 0)
    gsr = record.get('gsr_adc', 0)

    if bpm > 0:
        if bpm < clean_thresholds["bpm"]["min"] or bpm > clean_thresholds["bpm"]["max"]:
            issues.append("BPM_OUT_OF_RANGE")
    if spo2 > 0:
        if spo2 < clean_thresholds["spo2"]["min"] or spo2 > clean_thresholds["spo2"]["max"]:
            issues.append("SPO2_OUT_OF_RANGE")
    if body_temp > 0:
        if body_temp < clean_thresholds["body_temp"]["min"] or body_temp > clean_thresholds["body_temp"]["max"]:
            issues.append("TEMP_OUT_OF_RANGE")
    if gsr > 0:
        if gsr < clean_thresholds["gsr_adc"]["min"] or gsr > clean_thresholds["gsr_adc"]["max"]:
            issues.append("GSR_OUT_OF_RANGE")

    if not issues:
        return "CLEAN", "All vitals within normal range"
    else:
        return "QUESTIONABLE", "; ".join(issues)


def analyze_dataset(data):
    """Phan tich toan bo dataset."""
    print("\n" + "=" * 60)
    print("PHAN TICH DATASET")
    print("=" * 60)

    print(f"\n1. Tong quan:")
    print(f"   - Tong so records: {len(data)}")

    modes = Counter(r.get('mode', '?') for r in data)
    print(f"\n2. Mode distribution: {dict(modes)}")

    zero_bpm = sum(1 for r in data if r.get('bpm', 0) == 0)
    zero_spo2 = sum(1 for r in data if r.get('spo2', 0) == 0)
    zero_temp = sum(1 for r in data if r.get('body_temp', 0) == 0)
    zero_gsr = sum(1 for r in data if r.get('gsr_adc', 0) == 0)
    print(f"\n3. Records voi gia tri = 0:")
    print(f"   - BPM=0: {zero_bpm} ({100*zero_bpm/len(data):.1f}%)")
    print(f"   - SpO2=0: {zero_spo2} ({100*zero_spo2/len(data):.1f}%)")
    print(f"   - Body Temp=0: {zero_temp} ({100*zero_temp/len(data):.1f}%)")
    print(f"   - GSR=0: {zero_gsr} ({100*zero_gsr/len(data):.1f}%)")

    valid = [r for r in data if all([
        r.get('bpm', 0) > 0,
        r.get('spo2', 0) > 0,
        r.get('body_temp', 0) > 0,
        r.get('gsr_adc', 0) > 0
    ])]
    print(f"\n4. Records voi tat ca sensor > 0: {len(valid)} ({100*len(valid)/len(data):.1f}%)")

    if valid:
        print(f"\n5. Phan bo sensor (valid records):")
        bpms = [r['bpm'] for r in valid]
        print(f"   BPM: min={min(bpms)}, max={max(bpms)}, avg={sum(bpms)/len(bpms):.1f}")
        spo2s = [r['spo2'] for r in valid]
        print(f"   SpO2: min={min(spo2s)}, max={max(spo2s)}, avg={sum(spo2s)/len(spo2s):.1f}")
        temps = [r['body_temp'] for r in valid]
        print(f"   Body Temp: min={min(temps)}, max={max(temps)}, avg={sum(temps)/len(temps):.1f}")
        gsrs = [r['gsr_adc'] for r in valid]
        print(f"   GSR: min={min(gsrs)}, max={max(gsrs)}, avg={sum(gsrs)/len(gsrs):.1f}")

    labels = Counter(r.get('predicted_label', 'None') for r in data)
    print(f"\n6. predicted_label distribution: {dict(labels)}")

    return valid


def export_for_annotation(data, thresholds, warning_thresholds, clean_thresholds, output_path):
    """
    Xuat du lieu da loc ra CSV de gan nhan thu cong.
    """
    valid = [r for r in data if all([
        r.get('bpm', 0) > 0,
        r.get('spo2', 0) > 0,
        r.get('body_temp', 0) > 0,
        r.get('gsr_adc', 0) > 0
    ])]

    filtered = []
    for record in valid:
        reasons = check_filters(record, thresholds)
        if not reasons:
            filtered.append(record)

    print(f"\nXuat CSV voi {len(filtered)} records hop le (da loc nguong)")

    fieldnames = [
        'index',
        'timestamp_unix',
        'datetime',
        'device_id',
        'bpm',
        'spo2',
        'body_temp',
        'gsr_adc',
        'mode',
        # Engineered features
        'bpm_spo2_ratio',
        'temp_gsr_interaction',
        'bpm_temp_product',
        'spo2_gsr_ratio',
        'bpm_deviation',
        'temp_deviation',
        'gsr_deviation',
        'physiological_stress_index',
        # Old prediction (for reference only)
        'predicted_label_old',
        'confidence_old',
        # Suggested label (DO NOT USE FOR TRAINING - only for preview)
        'suggested_label',
        'suggestion_reason',
        # Data quality assessment
        'data_quality',
        'quality_notes',
        # MANUAL LABEL (TO BE FILLED BY EXPERT)
        'manual_label',
        'expert_notes',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for idx, record in enumerate(filtered):
            ts = record.get('timestamp', 0)
            try:
                dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            except:
                dt = "Invalid"

            suggested, reason = suggest_label(record, warning_thresholds)
            quality, quality_notes = assess_quality(record, clean_thresholds)

            row = {
                'index': idx + 1,
                'timestamp_unix': ts,
                'datetime': dt,
                'device_id': record.get('device_id', ''),
                'bpm': record.get('bpm', 0),
                'spo2': record.get('spo2', 0),
                'body_temp': record.get('body_temp', 0),
                'gsr_adc': record.get('gsr_adc', 0),
                'mode': record.get('mode', 0),
                # Engineered features
                'bpm_spo2_ratio': record.get('bpm_spo2_ratio', 0),
                'temp_gsr_interaction': record.get('temp_gsr_interaction', 0),
                'bpm_temp_product': record.get('bpm_temp_product', 0),
                'spo2_gsr_ratio': record.get('spo2_gsr_ratio', 0),
                'bpm_deviation': record.get('bpm_deviation', 0),
                'temp_deviation': record.get('temp_deviation', 0),
                'gsr_deviation': record.get('gsr_deviation', 0),
                'physiological_stress_index': record.get('physiological_stress_index', 0),
                # Old prediction
                'predicted_label_old': record.get('predicted_label', ''),
                'confidence_old': record.get('confidence', 0),
                # Suggested
                'suggested_label': suggested,
                'suggestion_reason': reason,
                # Data quality
                'data_quality': quality,
                'quality_notes': quality_notes,
                # Manual label
                'manual_label': '',
                'expert_notes': '',
            }
            writer.writerow(row)

    print(f"Da xuat CSV: {output_path}")
    return len(filtered)


def main():
    print("=" * 60)
    print("IoMT DATA FILTER & ANNOTATION EXPORTER")
    print("=" * 60)
    print(f"\nNguong filter (mo rong tam thoi):")
    for key, val in FILTER_THRESHOLDS.items():
        print(f"  - {key}: {val['min']} - {val['max']} {val['unit']}")

    data = load_data(INPUT_FILE)
    valid = analyze_dataset(data)
    count = export_for_annotation(
        data, FILTER_THRESHOLDS, WARNING_THRESHOLDS, CLEAN_THRESHOLDS, OUTPUT_FILE
    )

    print("\n" + "=" * 60)
    print("HOAN TAT")
    print("=" * 60)
    print(f"\nMo file CSV: {OUTPUT_FILE}")
    print("\nHUONG DAN GAN NHAN:")
    print("1. Mo file CSV bang Excel/Google Sheets")
    print("2. Cot 'manual_label' de gan nhan:")
    print("   - Normal: Sinh ly binh thuong")
    print("   - Warning: Co 1-2 chi so bat thuong nhe")
    print("   - Critical: Co chi so nguy hiem (SpO2<90, sot cao,...)")
    print("3. Cot 'expert_notes' de ghi chu them")
    print("\nLUU Y QUAN TRONG:")
    print("- Cot 'suggested_label' CHI de xem truoc, KHONG dung train model")
    print("- Nhan thuc te phai do chuyen gia/bac si gan")
    print("\nSau khi gan nhan xong, chay script huan luyen voi du lieu da gan nhan.")


if __name__ == "__main__":
    main()
