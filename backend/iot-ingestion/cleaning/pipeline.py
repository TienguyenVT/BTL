# -*- coding: utf-8 -*-
"""
Cleaning Pipeline Orchestrator.
Chạy 5 lớp làm sạch dữ liệu tuần tự.

Luồng xử lý:
  Raw Data → Lớp 1 (Hard Rules) → Lớp 2 (IQR) → Lớp 3 (IF+LOF)
           → Lớp 4 (KMeans) → Lớp 5 (Temporal) → Clean Data

Tham khảo: Pipeline tích hợp từ Health_Analysis.py
"""

from datetime import datetime
from typing import List

import pandas as pd

from models import TrainingHealthData
from cleaning.hard_rules import apply_hard_rules
from cleaning.iqr_filter import apply_iqr_filter
from cleaning.anomaly_detector import apply_anomaly_detection
from cleaning.label_validator import apply_label_validation
from cleaning.temporal_check import apply_temporal_check


class CleaningPipeline:
    """Orchestrator chạy pipeline làm sạch 5 lớp."""

    def run(self, raw_records: List[dict]) -> List[TrainingHealthData]:
        """
        Chạy pipeline làm sạch 5 lớp trên batch dữ liệu thô.

        Args:
            raw_records: Danh sách dict raw data từ ESP32/CSV

        Returns:
            Danh sách TrainingHealthData đã qua pipeline
        """
        print(f"\n{'='*60}")
        print(f"  PIPELINE LÀM SẠCH 5 LỚP - {len(raw_records)} bản ghi")
        print(f"{'='*60}")

        # Chuyển đổi list records → DataFrame để xử lý batch
        df = self._records_to_dataframe(raw_records)
        original_count = len(df)

        # ── Chạy 5 lớp tuần tự ──────────────────────────────────────
        df = apply_hard_rules(df)           # Lớp 1: Giới hạn sinh lý
        df = apply_iqr_filter(df)           # Lớp 2: IQR per label
        df = apply_anomaly_detection(df)    # Lớp 3: IF + LOF đồng thuận
        df = apply_label_validation(df)     # Lớp 4: KMeans validation
        df = apply_temporal_check(df)       # Lớp 5: Temporal consistency

        # ── Tổng kết ────────────────────────────────────────────────
        print(f"\n  ✓ Kết quả: {original_count} → {len(df)} bản ghi sạch "
              f"(giữ lại {len(df)/max(original_count,1)*100:.1f}%)")

        # Chuyển đổi DataFrame → list TrainingHealthData
        return self._dataframe_to_records(df)

    def _records_to_dataframe(self, records: List[dict]) -> pd.DataFrame:
        """Chuyển đổi list raw dict -> pandas DataFrame."""
        data = []
        for r in records:
            row = {
                "device_id": r.get("device_id", "CSV_IMPORT"),
                "user_id": r.get("user_id", ""),
                "timestamp": r.get("timestamp", datetime.utcnow()),
                "bpm": r.get("bpm", 0),
                "spo2": r.get("spo2", 0),
                "body_temp": r.get("body_temp", 0),
                "gsr_adc": r.get("gsr_adc", 0),
                "ext_temp_c": r.get("ext_temp_c", 0),
                "ext_humidity_pct": r.get("ext_humidity_pct", 0),
            }
            # Truyền label và time_slot nếu có (quan trọng cho Lớp 1-5)
            if "label" in r:
                row["label"] = r["label"]
            if "time_slot" in r:
                row["time_slot"] = r["time_slot"]
            data.append(row)
        return pd.DataFrame(data)

    def _dataframe_to_records(self, df: pd.DataFrame) -> List[TrainingHealthData]:
        """Chuyển đổi DataFrame đã clean → list TrainingHealthData."""
        records = []
        for _, row in df.iterrows():
            records.append(TrainingHealthData(
                user_id=row.get("user_id", ""),
                timestamp=row.get("timestamp", datetime.utcnow()),
                bpm=round(float(row.get("bpm", 0)), 2),
                spo2=round(float(row.get("spo2", 0)), 2),
                body_temp=round(float(row.get("body_temp", 0)), 2),
                gsr_adc=round(float(row.get("gsr_adc", 0)), 2),
                ext_temp_c=round(float(row.get("ext_temp_c", 0)), 2),
                ext_humidity_pct=round(float(row.get("ext_humidity_pct", 0)), 2),
                label=row.get("label", "Normal"),
            ))
        return records
