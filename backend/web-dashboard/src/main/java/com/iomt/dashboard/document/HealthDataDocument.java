package com.iomt.dashboard.document;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * MongoDB Document Model - Dữ liệu sức khỏe đã được làm sạch.
 * <p>
 * Map tới collection "clean_health_data" - cùng collection mà
 * Python iot-ingestion module ghi vào sau pipeline 5 lớp.
 * </p>
 *
 * <b>QUAN TRỌNG:</b> Schema này phải đồng bộ với CleanHealthData trong Python module.
 * Các field name sử dụng snake_case (theo convention MongoDB/Python).
 *
 * Các trường dữ liệu:
 * - bpm:              Nhịp tim (MAX30102)
 * - spo2:             SpO2 (MAX30102)
 * - body_temp:        Nhiệt độ cơ thể (MCP9808)
 * - gsr_adc:          Điện trở da (ADC)
 * - ext_temp_c:       Nhiệt độ môi trường (DHT22)
 * - ext_humidity_pct: Độ ẩm (DHT22)
 * - label:            Kết quả phân loại (Normal/Stress/Fever)
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "realtime_health_data")  // Trùng với Python Realtime Module (Model dự đoán)
public class HealthDataDocument {

    @Id
    private String id;

    // ── Metadata ────────────────────────────────────────────────────
    @Field("device_id")
    private String deviceId;            // ID thiết bị ESP32

    @Field("user_id")
    private String userId;              // ID người dùng

    @Field("timestamp")
    private Instant timestamp;          // Thời điểm đo

    // ── Chỉ số sinh lý (Body Sensors) ──────────────────────────────
    @Field("bpm")
    private Double bpm;                 // Nhịp tim (beats per minute)

    @Field("spo2")
    private Double spo2;                // Độ bão hòa oxy (%)

    @Field("body_temp")
    private Double bodyTemp;            // Nhiệt độ cơ thể (°C)

    @Field("gsr_adc")
    private Double gsrAdc;              // Điện trở da (ADC value)

    // ── Chỉ số môi trường (Environmental Sensors) ──────────────────
    @Field("ext_temp_c")
    private Double extTempC;            // Nhiệt độ ngoài (°C)

    @Field("ext_humidity_pct")
    private Double extHumidityPct;      // Độ ẩm (%)

    // ── Kết quả phân loại ──────────────────────────────────────────
    @Field("label")
    private String label;               // Normal | Stress | Fever

    @Field("time_slot")
    private String timeSlot;            // Morning | Afternoon | Evening

    // ── Pipeline metadata ──────────────────────────────────────────
    @Field("cleaning_version")
    private String cleaningVersion;     // VD: "5-layer-v1"

    @Field("cleaned_at")
    private Instant cleanedAt;          // Thời điểm clean xong
}
