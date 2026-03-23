package com.iomt.dashboard.components.health;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

/**
 * Controller cực kỳ tối giản cho dữ liệu sức khỏe.
 * Trả thẳng dữ liệu từ MongoDB ra cho Frontend (bỏ qua mọi rườm rà).
 */
@RestController
@RequestMapping("/api/health")
@CrossOrigin(origins = "*")
public class HealthController {

    @Autowired
    private MongoTemplate mongoTemplate;

    // DTO cấu trúc y hệt MongoDB, tự động map sang JSON Frontend cần
    @org.springframework.data.mongodb.core.mapping.Document(collection = "realtime_health_data")
    public static class HealthData {
        public String id;
        @Field("user_id") public String userId;
        @Field("device_id") public String deviceId;
        public Instant timestamp; // Spring tự convert thành ISO-8601 string
        
        public Double bpm;
        public Double spo2;
        @Field("body_temp") public Double bodyTemp;
        @Field("gsr_adc") public Double gsrAdc;
        
        @Field("ext_temp_c") public Double extTempC;
        @Field("ext_humidity_pct") public Double extHumidityPct;
        
        public String label;
        @Field("time_slot") public String timeSlot;
    }

    // 1. API: /api/health/latest
    @GetMapping("/latest")
    public HealthData getLatest(@RequestParam(required = false) String userId) {
        Query query = new Query();
        if (userId != null && !userId.isBlank()) {
            query.addCriteria(Criteria.where("user_id").is(userId));
        }
        query.with(Sort.by(Sort.Direction.DESC, "timestamp"));
        query.limit(1);
        
        return mongoTemplate.findOne(query, HealthData.class);
    }

    // 2. API: /api/health/history
    @GetMapping("/history")
    public List<HealthData> getHistory(
            @RequestParam(required = false) String userId,
            @RequestParam(defaultValue = "24") int hours) {
            
        Query query = new Query();
        if (userId != null && !userId.isBlank()) {
            query.addCriteria(Criteria.where("user_id").is(userId));
        }
        
        Instant timeAgo = Instant.now().minus(hours, ChronoUnit.HOURS);
        query.addCriteria(Criteria.where("timestamp").gte(timeAgo));
        
        // Lịch sử thường vẽ biểu đồ từ cũ -> mới
        query.with(Sort.by(Sort.Direction.ASC, "timestamp"));
        
        return mongoTemplate.find(query, HealthData.class);
    }

    // 3. API: /api/health/recent
    @GetMapping("/recent")
    public List<HealthData> getRecent(
            @RequestParam(required = false) String userId,
            @RequestParam(defaultValue = "20") int limit) {
            
        Query query = new Query();
        if (userId != null && !userId.isBlank()) {
            query.addCriteria(Criteria.where("user_id").is(userId));
        }
        query.with(Sort.by(Sort.Direction.DESC, "timestamp"));
        query.limit(limit);
        
        return mongoTemplate.find(query, HealthData.class);
    }
}
