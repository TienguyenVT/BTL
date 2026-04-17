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

/**
 * Controller: Quan ly canh bao suc khoe.
 * Alert duoc tao tu dong boi he thong (AI).
 * Nguoi dung chi xem va xoa.
 *
 * Base path: /api/alerts
 *
 * ENDPOINTS:
 *    GET    /api/alerts           — Danh sach canh bao
 *    GET    /api/alerts/count     — Dem so canh bao chua doc
 *    GET    /api/alerts/unread    — Lay danh sach alert chua doc (cho popup)
 *    PATCH  /api/alerts/{id}/read — Danh dau alert da doc
 *    DELETE /api/alerts/{id}      — Xoa canh bao
 */
@RestController
@RequestMapping("/api/alerts")
@RequiredArgsConstructor
public class AlertController {

    private final MongoTemplate mongoTemplate;

    // ================================================================
    // GET /api/alerts
    //    Lay danh sach canh bao cua user.
    //    Output: List<AlertDto>
    // ================================================================
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

    // ================================================================
    // GET /api/alerts/count
    //    Dem so canh bao chua doc.
    //    Output: { "unreadCount": N }
    // ================================================================
    @GetMapping("/count")
    public ResponseEntity<Map<String, Long>> getCount(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("user_id").is(uid)
                .and("is_read").is(false));

        long count = mongoTemplate.count(query, AlertEntity.class);
        return ResponseEntity.ok(Map.of("unreadCount", count));
    }

    // ================================================================
    // GET /api/alerts/unread
    //    Lay danh sach alert chua doc (Stress/Fever) cho popup.
    //    Output: List<AlertDto>
    // ================================================================
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

    // ================================================================
    // PATCH /api/alerts/{id}/read
    //    Danh dau alert da doc.
    //    Output: 200 | 404
    // ================================================================
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

    // ================================================================
    // DELETE /api/alerts/{id}
    //    Xoa canh bao.
    //    Output: 204 | 404
    // ================================================================
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

    // ================================================================
    // Chuyen Entity -> DTO (ham ho tro)
    // ================================================================
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
