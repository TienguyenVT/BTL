package com.iomt.dashboard.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO Response - Dữ liệu sức khỏe trả về cho Frontend.
 * <p>
 * Tách biệt với Document model để:
 *   1. Kiểm soát field nào được expose ra API
 *   2. Tùy chỉnh format (VD: làm tròn số, format ngày giờ)
 *   3. Tránh expose internal ID hay metadata không cần thiết
 * </p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthDataResponse {

    private String deviceId;
    private String userId;
    private Instant timestamp;

    // Chỉ số sinh lý
    private Double bpm;                 // Nhịp tim
    private Double spo2;                // SpO2 (%)
    private Double bodyTemp;            // Nhiệt độ cơ thể (°C)
    private Double gsrAdc;              // Điện trở da

    // Chỉ số môi trường
    private Double extTempC;            // Nhiệt độ ngoài (°C)
    private Double extHumidityPct;      // Độ ẩm (%)

    // Phân loại
    private String label;               // Normal | Stress | Fever
    private String timeSlot;            // Morning | Afternoon | Evening
}
