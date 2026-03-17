# -*- coding: utf-8 -*-
"""
Entry Point - Khởi chạy IoT Ingestion Module.

Module này chỉ có nhiệm vụ:
  1. Xử lý dữ liệu định kỳ từ MongoDB.
  2. Tự động huấn luyện mô hình theo chu kỳ.
  
Cách chạy:
  $ python main.py
"""

import signal
import sys
import time
import threading

from config import settings
from database import db_connection
from service import IngestionService
from train_model import run_training_pipeline


def automated_training_job(interval_seconds: int = 3600):
    """Job chạy ngầm để tự động huấn luyện lại mô hình sau mỗi khoảng thời gian."""
    while True:
        print("[MAIN] Bắt đầu tiến trình tự động huấn luyện mô hình...")
        try:
            success = run_training_pipeline()
            if success:
                print(f"[MAIN] Đã hoàn thành huấn luyện. Đợi {interval_seconds} giây cho lần tiếp theo.")
            else:
                print(f"[MAIN] Huấn luyện thất bại hoặc không có dữ liệu. Đợi {interval_seconds} giây.")
        except Exception as e:
            print(f"[MAIN] Lỗi trong quá trình huấn luyện: {e}")
            
        time.sleep(interval_seconds)


def main():
    """Khởi chạy toàn bộ IoT Ingestion Module (Chỉ xử lý DB)."""

    print("=" * 60)
    print("  IoMT - IoT INGESTION MODULE")
    print("  Xử lý dữ liệu sức khỏe định kỳ từ MongoDB")
    print("=" * 60)

    # ── Khởi tạo Service ─────────────────────────────────────────
    service = IngestionService()

    # ── Xử lý tín hiệu tắt (Graceful Shutdown) ──────────────────
    def shutdown_handler(signum, frame):
        print("\n[MAIN] ⚠ Đang dừng hệ thống...")
        service.flush_buffer()      # Xử lý nốt data
        db_connection.close()        # Đóng MongoDB
        print("[MAIN] ✓ Đã dừng hoàn toàn.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # ── Khởi chạy Thread Huấn luyện tự động ─────────────────────
    # Ở đây set tạm 60 giây (1 phút) để demo, thực tế nên là 3600 (1 giờ) hoặc 86400 (1 ngày)
    train_thread = threading.Thread(target=automated_training_job, args=(60,), daemon=True)
    train_thread.start()

    # ── Main Loop (Mô phỏng xử lý Ingestion nếu cần) ─────────────
    print(f"[MAIN] ▶ Đang chạy hệ thống (Nhấn Ctrl+C để thoát)...")
    try:
        while True:
            # Code xử lý dữ liệu realtime khác nếu có
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
