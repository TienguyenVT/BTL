# -*- coding: utf-8 -*-
"""Them DHT11 fields (room_temp, humidity) vao Node-RED flow JSON."""
import json, re

FLOW_PATH = r"c:\Documents\BTL\node_red_flow.json"

with open(FLOW_PATH, "r", encoding="utf-8") as f:
    content = f.read()

data = json.loads(content)

# ── 1. Cap nhat Filter & Normalize function ───────────────────────
for node in data:
    if node.get("id") == "func_filter_normalize":
        old_func = node["func"]

        # 1a. Them default cho room_temp + humidity
        old_func = old_func.replace(
            'd.gsr_adc   = (d.gsr_adc !== undefined)   ? d.gsr_adc   : 0;\n\n// 4. Cast to float',
            'd.gsr_adc   = (d.gsr_adc !== undefined)   ? d.gsr_adc   : 0;\n'
            '// 3b. DHT11: room temperature & humidity (optional, default 0)\n'
            'd.room_temp = (d.room_temp !== undefined) ? d.room_temp : 0;\n'
            'd.humidity  = (d.humidity  !== undefined) ? d.humidity  : 0;\n\n'
            '// 4. Cast to float'
        )

        # 1b. Them parseFloat cho 2 bien moi
        old_func = old_func.replace(
            'var gsr_adc   = parseFloat(d.gsr_adc);\n\n// 5. Outlier rejection',
            'var gsr_adc   = parseFloat(d.gsr_adc);\n'
            'var room_temp = parseFloat(d.room_temp);\n'
            'var humidity  = parseFloat(d.humidity);\n\n'
            '// 5. Outlier rejection'
        )

        # 1c. Validation cho room_temp (DHT11: -40..80 C, reject if >0 and out)
        old_func = old_func.replace(
            "if (gsr_adc < 0) {\n    node.warn('GSR negative (' + gsr_adc + ') — dropping');\n    return null;\n}\n\n// 6. Save raw backup",
            "if (gsr_adc < 0) {\n"
            "    node.warn('GSR negative (' + gsr_adc + ') — dropping');\n"
            "    return null;\n"
            "}\n"
            "// 5b. DHT11 validation: room_temp -40..80, humidity 0..100\n"
            "if (room_temp !== 0 && (room_temp < -40 || room_temp > 80)) {\n"
            "    node.warn('room_temp out of range (' + room_temp + ') — dropping');\n"
            "    return null;\n"
            "}\n"
            "if (humidity !== 0 && (humidity < 0 || humidity > 100)) {\n"
            "    node.warn('humidity out of range (' + humidity + ') — dropping');\n"
            "    return null;\n"
            "}\n\n"
            "// 6. Save raw backup"
        )

        # 1d. Them room_temp + humidity vao raw_backup
        old_func = old_func.replace(
            "    gsr_adc: gsr_adc,\n    ingested_at: new Date()",
            "    gsr_adc: gsr_adc,\n    room_temp: room_temp,\n    humidity: humidity,\n    ingested_at: new Date()"
        )

        # 1e. Them room_temp + humidity vao payload gui tiep
        old_func = old_func.replace(
            '    body_temp: body_temp,\n    gsr_adc: gsr_adc,\n    mode: d.mode\n};\n\nreturn msg;',
            '    body_temp: body_temp,\n    gsr_adc: gsr_adc,\n    room_temp: room_temp,\n    humidity: humidity,\n    mode: d.mode\n};\n\nreturn msg;'
        )

        node["func"] = old_func
        print("[OK] Cap nhat func_filter_normalize")
        break

# ── 2. Cap nhat Feature Engineering function ──────────────────────
for node in data:
    if node.get("id") == "func_feature_eng":
        old_func = node["func"]

        # Them 2 features moi: heat_index vao stress index, comfort_index
        old_func = old_func.replace(
            '// 8. physiological_stress_index = (bpm - 75)/75 + (gsr_adc - 2200)/2200\n'
            'd.physiological_stress_index = (bpm - 75) / 75 + (gsr_adc - 2200) / 2200;\n\n'
            'msg.payload = d;\n'
            'return msg;',
            '// 8. physiological_stress_index = (bpm - 75)/75 + (gsr_adc - 2200)/2200\n'
            'd.physiological_stress_index = (bpm - 75) / 75 + (gsr_adc - 2200) / 2200;\n\n'
            '// 9. heat_index = body_temp + 0.05 * humidity (DHT11)\n'
            'd.heat_index = body_temp + 0.05 * humidity;\n\n'
            '// 10. comfort_index = based on room_temp + humidity (DHT11)\n'
            '//    0=uncomfortable, 1=comfortable, -1=cold/heat stress\n'
            'var ideal_room_temp = 25; // comfortable room temp C\n'
            'var ideal_humidity  = 60; // comfortable humidity %\n'
            'd.comfort_index = 1.0 - Math.abs(room_temp - ideal_room_temp) / 20\n'
            '                         - Math.abs(humidity  - ideal_humidity) / 100;\n'
            'd.comfort_index = Math.max(-1, Math.min(1, d.comfort_index));\n\n'
            'msg.payload = d;\n'
            'return msg;'
        )

        node["func"] = old_func
        print("[OK] Cap nhat func_feature_eng: them 2 features moi")
        break

# ── 3. Cap nhat Build Data Lake function ─────────────────────────
for node in data:
    if node.get("id") == "func_attach_label":
        old_func = node["func"]

        # 3a. Them KEPT_FIELDS
        old_func = old_func.replace(
            'var KEPT_FIELDS = [\n    "bpm","spo2","body_temp","gsr_adc",\n    "bpm_spo2_ratio","temp_gsr_interaction","bpm_temp_product","spo2_gsr_ratio",\n    "bpm_deviation","temp_deviation","gsr_deviation","physiological_stress_index"\n];',
            'var KEPT_FIELDS = [\n    "bpm","spo2","body_temp","gsr_adc",\n    "bpm_spo2_ratio","temp_gsr_interaction","bpm_temp_product","spo2_gsr_ratio",\n    "bpm_deviation","temp_deviation","gsr_deviation","physiological_stress_index",\n    "heat_index","comfort_index"  // DHT11 features\n];'
        )

        # 3b. Them sensor.room_temp + sensor.humidity
        old_func = old_func.replace(
            '    sensor: {\n        bpm:       rawPayload.bpm,\n        spo2:      rawPayload.spo2,\n        body_temp: rawPayload.body_temp,\n        gsr_adc:   rawPayload.gsr_adc\n    },',
            '    sensor: {\n        bpm:       rawPayload.bpm,\n        spo2:      rawPayload.spo2,\n        body_temp: rawPayload.body_temp,\n        gsr_adc:   rawPayload.gsr_adc,\n        room_temp: rawPayload.room_temp,\n        humidity:  rawPayload.humidity\n    },'
        )

        # 3c. Them features heat_index + comfort_index
        old_func = old_func.replace(
            '        gsr_deviation:             sensor.gsr_deviation,\n        physiological_stress_index:  sensor.physiological_stress_index\n    },',
            '        gsr_deviation:             sensor.gsr_deviation,\n        physiological_stress_index:  sensor.physiological_stress_index,\n        heat_index:               sensor.heat_index,\n        comfort_index:             sensor.comfort_index\n    },'
        )

        node["func"] = old_func
        print("[OK] Cap nhat func_attach_label: sensor + features")
        break

# ── 4. Luu file
with open(FLOW_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("\n[OK] Luu node_red_flow.json")

# Verify
with open(FLOW_PATH, "r", encoding="utf-8") as f:
    data2 = json.load(f)

for node in data2:
    if node.get("id") == "func_filter_normalize":
        print("\n[CHECK] room_temp in Filter func:", "room_temp" in node["func"])
        print("[CHECK] humidity  in Filter func:", "humidity" in node["func"])
    if node.get("id") == "func_feature_eng":
        print("[CHECK] heat_index    in FE func:", "heat_index" in node["func"])
        print("[CHECK] comfort_index in FE func:", "comfort_index" in node["func"])
    if node.get("id") == "func_attach_label":
        print("[CHECK] room_temp in BuildDL func:", "room_temp" in node["func"])
        print("[CHECK] humidity  in BuildDL func:", "humidity" in node["func"])
        print("[CHECK] heat_index    in BuildDL func:", "heat_index" in node["func"])
        print("[CHECK] comfort_index in BuildDL func:", "comfort_index" in node["func"])
