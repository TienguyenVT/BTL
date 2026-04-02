package com.iomt.dashboard.components.health;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * Entity: Phiên đo (Session) — nhóm các bản ghi final_result theo phiên sử dụng.
 * Collection: "sessions"
 *
 * Mỗi phiên đại diện cho một lần đo liên tục của người dùng.
 * Hai bản ghi cách nhau > 15 phút → phiên mới.
 *
 * Các trường:
 *    - sessionId    : UUID định danh phiên
 *    - startTime    : ingested_at của bản ghi đầu tiên
 *    - endTime      : ingested_at của bản ghi cuối cùng
 *    - recordCount  : số bản ghi trong phiên
 *    - label        : predicted_label chính (mode)
 *    - avgBpm       : trung bình BPM
 *    - avgSpo2      : trung bình SpO2
 *    - avgBodyTemp  : trung bình body_temp
 *    - avgGsrAdc    : trung bình gsr_adc
 *    - active       : true nếu bản ghi cuối cách hiện tại < 15 phút
 *    - updatedAt    : thời điểm cập nhật gần nhất
 */
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
