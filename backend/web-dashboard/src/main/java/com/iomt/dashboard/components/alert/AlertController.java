package com.iomt.dashboard.components.alert;

import com.iomt.dashboard.common.UserUtils;
import lombok.RequiredArgsConstructor;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/alerts")
@RequiredArgsConstructor
public class AlertController {

    private final MongoTemplate mongoTemplate;

    @GetMapping
    public ResponseEntity<List<AlertDto>> getAll(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("user_id").is(uid));
        query.with(org.springframework.data.domain.Sort.by(
                org.springframework.data.domain.Sort.Direction.DESC, "timestamp"
        ));

        List<AlertDto> alerts = mongoTemplate.find(query, AlertEntity.class)
                .stream()
                .map(this::toDto)
                .collect(Collectors.toList());

        return ResponseEntity.ok(alerts);
    }

    @GetMapping("/count")
    public ResponseEntity<Map<String, Long>> getCount(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("user_id").is(uid)
                .and("is_read").is(false));

        long count = mongoTemplate.count(query, AlertEntity.class);
        return ResponseEntity.ok(Map.of("unreadCount", count));
    }

    @GetMapping("/unread")
    public ResponseEntity<List<AlertDto>> getUnread(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(
                Criteria.where("user_id").is(uid)
                        .and("is_read").is(false)
                        .and("label").in("Stress", "Fever")
        );
        query.with(org.springframework.data.domain.Sort.by(
                org.springframework.data.domain.Sort.Direction.DESC, "timestamp"
        ));

        List<AlertDto> alerts = mongoTemplate.find(query, AlertEntity.class)
                .stream()
                .map(this::toDto)
                .collect(Collectors.toList());

        return ResponseEntity.ok(alerts);
    }

    @PatchMapping("/{id}/read")
    public ResponseEntity<Void> markAsRead(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(uid));

        AlertEntity alert = mongoTemplate.findOne(query, AlertEntity.class);
        if (alert == null) {
            return ResponseEntity.notFound().build();
        }

        Update update = new Update().set("is_read", true);
        mongoTemplate.updateFirst(query, update, AlertEntity.class);

        return ResponseEntity.ok().build();
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(uid));

        AlertEntity alert = mongoTemplate.findOne(query, AlertEntity.class);
        if (alert == null) {
            return ResponseEntity.notFound().build();
        }

        mongoTemplate.remove(alert);
        return ResponseEntity.noContent().build();
    }

    private AlertDto toDto(AlertEntity entity) {
        return new AlertDto(
                entity.id,
                entity.label,
                entity.message,
                entity.timestamp,
                entity.isRead,
                entity.bpm,
                entity.spo2,
                entity.bodyTemp,
                entity.gsrAdc,
                entity.confidence,
                entity.macAddress
        );
    }
}
