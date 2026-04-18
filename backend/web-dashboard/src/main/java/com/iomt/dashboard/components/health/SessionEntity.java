package com.iomt.dashboard.components.health;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "sessions")
public class SessionEntity {

    @Id
    public String id;

    @Indexed(unique = true)
    @Field("session_id")
    public String sessionId;

    @Field("start_time")
    public Instant startTime;

    @Field("end_time")
    public Instant endTime;

    @Field("record_count")
    public int recordCount;

    @Field("label")
    public String label;

    @Field("avg_bpm")
    public Double avgBpm;

    @Field("avg_spo2")
    public Double avgSpo2;

    @Field("avg_body_temp")
    public Double avgBodyTemp;

    @Field("avg_gsr_adc")
    public Double avgGsrAdc;

    @Field("active")
    public boolean active;

    @Field("updated_at")
    public Instant updatedAt;
}
