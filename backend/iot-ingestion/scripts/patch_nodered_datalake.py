# -*- coding: utf-8 -*-
"""
Patch Node-RED flow JSON:
  1. Cap nhat Function Node 3: xay dung datalake_raw document voi metadata day du
  2. Doi ten collection tu raw_sensor -> datalake_raw
  3. Xoa TTL index khoi collection moi (neu co)
  4. Cap nhat comment nodes cho chinh xac
"""
import json, os

FLOW_PATH = r"c:\Documents\BTL\node_red_flow.json"
BACKUP_PATH = FLOW_PATH + ".bak2"

# Backup
with open(FLOW_PATH, "r", encoding="utf-8") as f:
    original = f.read()
with open(BACKUP_PATH, "w", encoding="utf-8") as f:
    f.write(original)
print("[Backup] Da luu: " + BACKUP_PATH)

data = json.loads(original)

# ── 1. Cap nhat Function Node 3: Attach Label & Build Data Lake ──────────────
datalake_func = """// ══════════════════════════════════════════════════════════
// Function Node 3: Attach Label & Build Data Lake
//
// Luong xu ly:
//   - realtime_health_data: 12 engineered features (Datawarehouse)
//   - datalake_raw: full raw MQTT payload + rich metadata (Data Lake)
//
// Data Lake schema:
//   - source:       "mqtt_esp32" | "rest_api" | "csv_batch" | ...
//   - source_topic: topic MQTT goc
//   - device_id:    ESP32 device ID (hoac default)
//   - timestamp:    Unix ms tu ESP32
//   - mode:        ESP32 operation mode
//   - raw_payload: Tat ca cac truong nhan duoc tu MQTT
//   - sensor:       Normalized sensor values (bpm, spo2, body_temp, gsr_adc)
//   - data_quality: "raw" | "normalized" | "outlier_rejected"
//   - schema_version: "1.0" — de track thay doi schema trong tuong lai
//   - ingested_at:  Server timestamp khi nhan duoc message
//   - processing_latency_ms: Thoi gian tu ESP32 gui den khi luu (ms)
//
// ══════════════════════════════════════════════════════════

var sensor = msg.sensorPayload || {};
var httpResp = msg.payload;
var statusCode = msg.statusCode;
var rawPayload = msg.raw_backup || {};

// ── Merge prediction result onto stripped payload ──────────
var stripped = {};
var KEPT_FIELDS = [
    "bpm","spo2","body_temp","gsr_adc",
    "bpm_spo2_ratio","temp_gsr_interaction","bpm_temp_product","spo2_gsr_ratio",
    "bpm_deviation","temp_deviation","gsr_deviation","physiological_stress_index"
];
KEPT_FIELDS.forEach(function(f) {
    if (sensor[f] !== undefined) { stripped[f] = sensor[f]; }
});

// ── Build Data Lake document (rich metadata) ─────────────────
var latencyMs = (rawPayload.timestamp)
    ? (Date.now() - parseInt(rawPayload.timestamp))
    : null;

var datalakeDoc = {
    // ── Source identification ────────────────────────────────
    source:         "mqtt_esp32",
    source_topic:   "ptit/health/data",

    // ── Device & timing ─────────────────────────────────────
    device_id:      String(rawPayload.device_id || sensor.device_id || "unknown"),
    timestamp:      rawPayload.timestamp || Date.now(),
    mode:           rawPayload.mode !== undefined ? rawPayload.mode : null,

    // ── Raw MQTT payload (original, untouched) ──────────────
    raw_payload:    JSON.parse(JSON.stringify(rawPayload)),

    // ── Normalized sensor values ────────────────────────────
    sensor: {
        bpm:       rawPayload.bpm,
        spo2:      rawPayload.spo2,
        body_temp: rawPayload.body_temp,
        gsr_adc:   rawPayload.gsr_adc
    },

    // ── Engineered features (from feature engineering node) ─
    features: {
        bpm_spo2_ratio:             sensor.bpm_spo2_ratio,
        temp_gsr_interaction:       sensor.temp_gsr_interaction,
        bpm_temp_product:           sensor.bpm_temp_product,
        spo2_gsr_ratio:             sensor.spo2_gsr_ratio,
        bpm_deviation:             sensor.bpm_deviation,
        temp_deviation:             sensor.temp_deviation,
        gsr_deviation:             sensor.gsr_deviation,
        physiological_stress_index:  sensor.physiological_stress_index
    },

    // ── Prediction result ────────────────────────────────────
    prediction: (statusCode === 200 && httpResp && httpResp.predicted_label)
        ? {
            label:      httpResp.predicted_label,
            confidence: httpResp.confidence
        }
        : null,

    // ── Pipeline metadata ───────────────────────────────────
    data_quality:    rawPayload.bpm !== 0 && rawPayload.spo2 !== 0 && rawPayload.body_temp !== 0
                        ? "normalized" : "raw",
    schema_version:  "1.0",
    ingested_at:     new Date(),
    processing_latency_ms: latencyMs
};

// ── Output 1: realtime_health_data (Datawarehouse) ──────
// Fields: 12 features only (MongoDB auto-adds _id on insert)
var msg1 = { payload: stripped };

// ── Output 2: datalake_raw (Data Lake) ────────────────
var msg2 = { payload: datalakeDoc };

return [msg1, msg2];
"""

# ── 2. Doi ten collection tu raw_sensor -> datalake_raw ──────────
NEW_COLLECTION_NAME = "datalake_raw"

for node in data:
    # Cap nhat Function Node 3
    if node.get("id") == "func_attach_label":
        node["name"] = "3. Build Data Lake & Strip Features"
        node["func"] = datalake_func
        print("[Patch 1] func_attach_label: da xay dung datalake_doc voi metadata day du")

    # Doi ten mongo_raw node
    if node.get("id") == "mongo_raw":
        node["name"] = "Save -> datalake_raw"
        node["collection"] = NEW_COLLECTION_NAME
        print("[Patch 2] mongo_raw: doi ten collection thanh datalake_raw")

    # Cap nhat comment Data Lake
    if node.get("id") == "comment_pipeline":
        node["info"] = (
            "Architecture: Node-RED Streaming ETL\n\n"
            "1. MQTT In: ptit/health/data tu HiveMQ Cloud\n"
            "2. Filter & Normalize: Validate + outlier rejection\n"
            "3. Feature Engineering: 8 derived features (mirrors train_model.py)\n"
            "4. HTTP POST /predict: Python FastAPI ML endpoint\n"
            "5. Build Data Lake: luu raw MQTT payload + rich metadata\n"
            "6. MongoDB Output:\n"
            "   - realtime_health_data: 12 engineered features (Datawarehouse)\n"
            "   - datalake_raw: raw payload + metadata (Data Lake, vĩnh viễn)\n\n"
            "Data Lake Schema (datalake_raw):\n"
            "   source, source_topic, device_id, timestamp, mode,\n"
            "   raw_payload, sensor, features, prediction,\n"
            "   data_quality, schema_version, ingested_at, processing_latency_ms\n\n"
            "Luu y:\n"
            "   - Python server phai chay tai http://localhost:8000\n"
            "   - Hay import lai MQTT credentials sau khi import flow"
        )
        print("[Patch 3] comment_pipeline: cap nhat noi dung mieu ta")

print("[OK] Tat ca patches da ap dung!")

# Ghi lai
with open(FLOW_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("\nLuu y: Hay import lai flow vao Node-RED de ap dung thay doi.")
print("Sau khi deploy, xoa TTL index tren raw_sensor (neu con) bang:")
print("  db.raw_sensor.dropIndex('ingested_at_1')")
