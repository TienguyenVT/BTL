# -*- coding: utf-8 -*-
"""
Patch Node-RED flow JSON:
  1. func_attach_label: xoa ingested_at khoi realtime_health_data payload
  2. func_attach_label: cap nhat comment chan thanh cong cho 12 features
"""
import json, re, os

flow_path = r"c:\Documents\BTL\node_red_flow.json"
backup_path = flow_path + ".bak"

# Backup
with open(flow_path, "r", encoding="utf-8") as f:
    original = f.read()
with open(backup_path, "w", encoding="utf-8") as f:
    f.write(original)
print(f"[Backup] Da luu: {backup_path}")

data = json.loads(original)

for node in data:
    if node.get("id") == "func_attach_label":
        func_src = node["func"]

        # Patch 1: Loai bo ingested_at khoi stripped object (realtime_health_data)
        # Cu phap cu:  "// Add ingestion timestamp (kept for pipeline reference)\nstripped.ingested_at = new Date();\n"
        func_src = func_src.replace(
            '// Add ingestion timestamp (kept for pipeline reference)\n'
            'stripped.ingested_at = new Date();\n',
            ''
        )

        # Patch 2: Cap nhat comment cho realtime_health_data
        func_src = func_src.replace(
            '// Fields: 12 features + ingested_at (MongoDB auto-adds _id on insert)',
            '// Fields: 12 features only (MongoDB auto-adds _id on insert)'
        )

        node["func"] = func_src
        print(f"[Patch] func_attach_label: da loai bo ingested_at khoi realtime_health_data")
        break

# Ghi lai
with open(flow_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("[OK] node_red_flow.json da duoc cap nhat!")
print("\nLuu y: Hay import lai flow vao Node-RED de ap dung thay doi.")
