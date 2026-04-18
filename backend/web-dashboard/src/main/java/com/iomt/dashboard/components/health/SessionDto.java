package com.iomt.dashboard.components.health;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

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

    public List<HealthRecordDto> records;

    public String deviceId;

    public String deviceName;

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

        public String macAddress;
    }
}
