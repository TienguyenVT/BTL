package com.iomt.dashboard.components.health;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * DTO: Phiên đo (Session) — response trả về cho Frontend.
 *
 * Khi gọi /sessions/{id}:
 *    - records != null (danh sách đầy đủ bản ghi trong phiên)
 *
 * Khi gọi /sessions, /sessions/latest, /sessions/history:
 *    - records == null (chỉ metadata, không kèm records)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SessionDto {

    public String sessionId;

    public Instant startTime;

    public Instant endTime;

    public int recordCount;

    public String label;

    public Double avgBpm;

    public Double avgSpo2;

    public Double avgBodyTemp;

    public Double avgGsrAdc;

    public boolean active;

    /** Danh sách bản ghi — chỉ điền khi gọi /sessions/{id} */
    public List<HealthRecordDto> records;

    /**
     * DTO: Một bản ghi sức khỏe trong phiên.
     * Tương ứng với một document trong final_result.
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HealthRecordDto {
        public String id;
        public Double bpm;
        public Double spo2;
        public Double bodyTemp;
        public Double gsrAdc;
        public Double extTempC;
        public Double extHumidityPct;
        public String label;
        public Double confidence;
        public Instant timestamp;
        public Instant ingestedAt;
    }
}
