package com.iomt.dashboard.components.health;

import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Service: Phát hiện và quản lý phiên đo (Session).
 *
 * Luồng xử lý:
 * 1. Doc ALL records tu final_result, sort theo ingested_at ASC
 * 2. Quet lan luot: neu 2 ban ghi cach nhau > 15 phut → phiên mới
 * 3. Moi phiên: tinh avg, label chinh (mode cua predicted_label)
 * 4. active = (hieu thoi gian tu ban ghi cuoi cung den hien tai < 15 phut)
 * 5. LUU: chi save/update phiên moi hoac phiên active
 */
@Service
@RequiredArgsConstructor
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);

    /** Khoảng gap (ms) de nhan biet phiên mới: 15 phút */
    private static final long SESSION_GAP_MS = 15 * 60 * 1000L;

    /** ESP32 gửi timestamp ở múi giờ Việt Nam UTC+7 */
    private static final ZoneOffset VN_ZONE = ZoneOffset.ofHours(7);

    /** DateTimeFormatter parse chuoi "yyyy:MM:dd - HH:mm:ss" */
    private static final DateTimeFormatter TS_PARSE_FMT = DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss");

    private final MongoTemplate mongoTemplate;

    // ================================================================
    // Public API
    // ================================================================

    /**
     * Tra ve danh sach TAT CA phiên đo, sap xep theo startTime DESC.
     */
    public List<SessionDto> getAllSessions() {
        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> entities = mongoTemplate.find(query, SessionEntity.class, "sessions");
        return entities.stream().map(this::toDto).toList();
    }

    /**
     * Tra ve danh sach phiên trong khoang N gio gan day.
     */
    public List<SessionDto> getSessionsInRange(int hours) {
        Instant timeAgo = Instant.now().minus(hours, ChronoUnit.HOURS);
        Query query = new Query(
                new org.springframework.data.mongodb.core.query.Criteria("start_time").gte(timeAgo)
        ).with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> entities = mongoTemplate.find(query, SessionEntity.class, "sessions");
        return entities.stream().map(this::toDto).toList();
    }

    /**
     * Tra ve PHIEN ACTIVE cuoi cung (dang theo doi, chua bi ngat).
     * active = true khi ban ghi cuoi cung cach hien tai < 15 phut.
     */
    public SessionDto getLatestActiveSession() {
        Query query = new Query(
                new org.springframework.data.mongodb.core.query.Criteria("active").is(true)
        ).with(Sort.by(Sort.Direction.DESC, "start_time")).limit(1);
        SessionEntity entity = mongoTemplate.findOne(query, SessionEntity.class, "sessions");
        if (entity == null) {
            return null;
        }
        return toDtoWithRecords(entity);
    }

    /**
     * Tra ve session active — query TRỰC TIẾP final_result mà không qua sessions collection.
     * Fixes race condition: frontend không phụ thuộc vào rebuild timing.
     *
     * Logic:
     * 1. Lay ban ghi moi nhat trong final_result
     * 2. Neu co gap > 15 phut so voi ban ghi truoc do → session moi
     * 3. Tra ve session hien tai (tinh toan tai thoi diem query, khong dung rebuild)
     */
    public SessionDto getLiveSession() {
        Instant now = Instant.now();
        Instant sessionGapBoundary = now.minus(SESSION_GAP_MS, ChronoUnit.MILLIS);

        // Lay 1 ban ghi moi nhat de biet thoi diem gap
        Query latestQuery = new Query()
                .with(Sort.by(Sort.Direction.DESC, "ingested_at"))
                .limit(1);
        Document latestDoc = mongoTemplate.findOne(latestQuery, Document.class, "final_result");

        if (latestDoc == null) {
            return null;
        }

        Instant latestIngestedAt = parseIngestedAt(latestDoc.get("ingested_at"));

        // Xac dinh session active: latest - SESSION_GAP_MS < latestIngestedAt
        // active = (now - latestIngestedAt) < 15 phut
        boolean isActive = Math.abs(now.toEpochMilli() - latestIngestedAt.toEpochMilli()) < SESSION_GAP_MS;

        if (!isActive) {
            // Khong co session active
            return null;
        }

        // Lay ALL records cua session active:
        // Session active = tat ca records tu latestIngestedAt nguoc lai den khi gap > 15 phut
        // Lay records tu (latestIngestedAt - SESSION_GAP_MS) den now
        Instant sessionStart = latestIngestedAt.minus(SESSION_GAP_MS, ChronoUnit.MILLIS);

        // Loc chi nhung records co ingested_at >= sessionStart
        // (vi nhung record cu hon sessionStart co nghia la thuoc session cu)
        Query recordsQuery = new Query(
                new org.springframework.data.mongodb.core.query.Criteria("ingested_at").gte(sessionStart)
        ).with(Sort.by(Sort.Direction.ASC, "ingested_at"));

        List<Document> docs = mongoTemplate.find(recordsQuery, Document.class, "final_result");

        if (docs.isEmpty()) {
            return null;
        }

        // Xac dinh chinh xac start/end cua session tu docs thuc te
        Instant actualStart = parseIngestedAt(docs.get(0).get("ingested_at"));
        Instant actualEnd = parseIngestedAt(docs.get(docs.size() - 1).get("ingested_at"));

        // Loc nhung record thuc su thuoc session (nghĩa là: ko co gap > 15 phut)
        List<Document> sessionDocs = new ArrayList<>();
        Instant currentSessionStart = actualStart;
        for (Document doc : docs) {
            Instant docTime = parseIngestedAt(doc.get("ingested_at"));
            if (Math.abs(docTime.toEpochMilli() - currentSessionStart.toEpochMilli()) > SESSION_GAP_MS) {
                // Gap > 15 phut → bat dau session moi, dung lai
                break;
            }
            sessionDocs.add(doc);
            if (docTime.isAfter(currentSessionStart)) {
                currentSessionStart = docTime;
            }
        }

        // Build SessionDto (khong luu vao sessions collection — chi tra ve)
        SessionDto dto = new SessionDto();
        dto.setSessionId("live-" + latestIngestedAt.toEpochMilli());
        dto.setStartTime(sessionDocs.isEmpty() ? actualStart : parseIngestedAt(sessionDocs.get(0).get("ingested_at")));
        dto.setEndTime(sessionDocs.isEmpty() ? actualEnd : parseIngestedAt(sessionDocs.get(sessionDocs.size() - 1).get("ingested_at")));
        dto.setRecordCount(sessionDocs.size());
        dto.setActive(true);

        // Tinh avg tu sessionDocs
        dto.setAvgBpm(computeAvg(sessionDocs, "bpm"));
        dto.setAvgSpo2(computeAvg(sessionDocs, "spo2"));
        dto.setAvgBodyTemp(computeAvg(sessionDocs, "body_temp"));
        dto.setAvgGsrAdc(computeAvg(sessionDocs, "gsr_adc"));
        dto.setLabel(computeModeLabel(sessionDocs));

        // Chuyen thanh HealthRecordDto
        List<SessionDto.HealthRecordDto> records = sessionDocs.stream()
                .map(this::docToRecord)
                .toList();
        dto.setRecords(records);

        return dto;
    }

    private Double computeAvg(List<Document> docs, String field) {
        List<Double> values = docs.stream()
                .map(doc -> {
                    Object v = doc.get(field);
                    if (v == null) return null;
                    if (v instanceof Number n) return n.doubleValue();
                    try { return Double.parseDouble(v.toString()); }
                    catch (Exception e) { return null; }
                })
                .filter(Objects::nonNull)
                .toList();
        if (values.isEmpty()) return null;
        return values.stream().mapToDouble(d -> d).average().orElse(Double.NaN);
    }

    private String computeModeLabel(List<Document> docs) {
        Map<String, Long> counts = docs.stream()
                .map(doc -> doc.getString("label"))
                .filter(Objects::nonNull)
                .collect(Collectors.groupingBy(l -> l, Collectors.counting()));
        if (counts.isEmpty()) return null;
        return counts.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse(null);
    }

    /**
     * Tra ve chi tiet 1 phiên (kem danh sach records).
     */
    public SessionDto getSessionById(String sessionId) {
        Query query = new Query(
                new org.springframework.data.mongodb.core.query.Criteria("session_id").is(sessionId)
        );
        SessionEntity entity = mongoTemplate.findOne(query, SessionEntity.class, "sessions");
        if (entity == null) {
            return null;
        }
        return toDtoWithRecords(entity);
    }

    // ================================================================
    // Session Rebuild (goi tu Scheduler)
    // ================================================================

    /**
     * Quet toan bo final_result, phat hien phiên moi / cap nhat phiên active,
     * LUU ket qua vao bang sessions.
     *
     * Chay moi 30 giay (tu SessionScheduler).
     */
    public void rebuildSessions() {
        log.info("[SessionService] Starting session rebuild...");

        // 1. Doc ALL records tu final_result, sort ASC
        Query query = new Query().with(Sort.by(Sort.Direction.ASC, "ingested_at"));
        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        if (docs.isEmpty()) {
            log.info("[SessionService] final_result is empty, no sessions to build.");
            return;
        }

        // 2. Phat hien phiên bang cach gap > 15 phut
        List<SessionGroup> groups = detectSessions(docs);
        log.info("[SessionService] Detected {} sessions from {} records.", groups.size(), docs.size());

        Instant now = Instant.now();

        // 3. Danh sach session_id hien co trong DB
        Set<String> existingIds = mongoTemplate.find(
                new Query(), SessionEntity.class, "sessions"
        ).stream()
                .map(e -> e.getSessionId())
                .collect(Collectors.toSet());

        for (SessionGroup group : groups) {
            Instant lastRecordTime = group.endTime;
            boolean isActive = Math.abs(now.toEpochMilli() - lastRecordTime.toEpochMilli()) < SESSION_GAP_MS;

            // Kiem tra xem phiên nay da ton tai chua
            SessionEntity existing = findBySessionId(group.sessionId);

            if (existing == null) {
                // Phiên mới — insert
                SessionEntity entity = buildEntity(group, isActive);
                mongoTemplate.insert(entity, "sessions");
                log.debug("[SessionService] Inserted new session: {}", group.sessionId);
            } else if (existing.isActive() || needsUpdate(existing, group)) {
                // Phiên active hoac co thay doi — cap nhat
                updateEntity(existing, group, isActive);
                mongoTemplate.save(existing, "sessions");
                log.debug("[SessionService] Updated session: {}", group.sessionId);
            }
        }

        // 4. Danh sach session_id moi phat hien
        Set<String> newIds = groups.stream()
                .map(g -> g.sessionId)
                .collect(Collectors.toSet());

        // 5. Danh sach phiên can de-activate (ton tai nhung khong con trong final_result)
        Set<String> toDeactivate = new HashSet<>(existingIds);
        toDeactivate.removeAll(newIds);

        for (String sid : toDeactivate) {
            SessionEntity entity = findBySessionId(sid);
            if (entity != null && entity.isActive()) {
                entity.setActive(false);
                entity.setUpdatedAt(now);
                mongoTemplate.save(entity, "sessions");
                log.debug("[SessionService] Deactivated session: {}", sid);
            }
        }

        log.info("[SessionService] Session rebuild complete. Active sessions: {}",
                groups.stream().filter(g -> {
                    long diff = now.toEpochMilli() - g.endTime.toEpochMilli();
                    return diff < SESSION_GAP_MS;
                }).count());
    }

    // ================================================================
    // Private helpers
    // ================================================================

    /**
     * Phat hien cac phiên tu danh sach documents.
     * Gap > 15 phut giua 2 ban ghi lien tiep → phiên mới.
     */
    private List<SessionGroup> detectSessions(List<Document> docs) {
        List<SessionGroup> groups = new ArrayList<>();
        SessionGroup current = null;

        for (Document doc : docs) {
            Instant ingestedAt = parseIngestedAt(doc.get("ingested_at"));

            if (current == null) {
                current = new SessionGroup(UUID.randomUUID().toString(), ingestedAt);
            } else if (Math.abs(ingestedAt.toEpochMilli() - current.endTime.toEpochMilli()) > SESSION_GAP_MS) {
                // Gap > 15 phut → kết thúc phiên hiện tại, bắt đầu phiên mới
                groups.add(current);
                current = new SessionGroup(UUID.randomUUID().toString(), ingestedAt);
            }

            current.addRecord(doc);
        }

        if (current != null) {
            groups.add(current);
        }

        return groups;
    }

    /** Parse ingested_at (java.util.Date / Instant / LocalDateTime / String) */
    private Instant parseIngestedAt(Object value) {
        if (value == null) return Instant.now();
        if (value instanceof java.util.Date date) return date.toInstant();
        if (value instanceof Instant instant) return instant;
        if (value instanceof LocalDateTime ldt) return ldt.toInstant(ZoneOffset.UTC);
        try {
            return Instant.parse(value.toString());
        } catch (Exception e) {
            // Fallback: thử parse string timestamp "yyyy:MM:dd - HH:mm:ss"
            // Đây là ESP32 format — parse as UTC+7
            try {
                LocalDateTime ldt = LocalDateTime.parse(value.toString(), TS_PARSE_FMT);
                return ldt.toInstant(VN_ZONE);
            } catch (Exception ex) {
                log.warn("[SessionService] Could not parse ingested_at '{}', using now.", value);
                return Instant.now();
            }
        }
    }

    private SessionEntity findBySessionId(String sessionId) {
        return mongoTemplate.findOne(
                new Query(new org.springframework.data.mongodb.core.query.Criteria("session_id").is(sessionId)),
                SessionEntity.class, "sessions"
        );
    }

    private SessionEntity buildEntity(SessionGroup group, boolean active) {
        SessionEntity entity = new SessionEntity();
        entity.setSessionId(group.sessionId);
        entity.setStartTime(group.startTime);
        entity.setEndTime(group.endTime);
        entity.setRecordCount(group.records.size());
        entity.setLabel(group.computeModeLabel());
        entity.setAvgBpm(group.computeAvg("bpm"));
        entity.setAvgSpo2(group.computeAvg("spo2"));
        entity.setAvgBodyTemp(group.computeAvg("body_temp"));
        entity.setAvgGsrAdc(group.computeAvg("gsr_adc"));
        entity.setActive(active);
        entity.setUpdatedAt(Instant.now());
        return entity;
    }

    private void updateEntity(SessionEntity entity, SessionGroup group, boolean active) {
        entity.setEndTime(group.endTime);
        entity.setRecordCount(group.records.size());
        entity.setLabel(group.computeModeLabel());
        entity.setAvgBpm(group.computeAvg("bpm"));
        entity.setAvgSpo2(group.computeAvg("spo2"));
        entity.setAvgBodyTemp(group.computeAvg("body_temp"));
        entity.setAvgGsrAdc(group.computeAvg("gsr_adc"));
        entity.setActive(active);
        entity.setUpdatedAt(Instant.now());
    }

    private boolean needsUpdate(SessionEntity existing, SessionGroup group) {
        // Cap nhat neu so ban ghi thay doi hoac endTime thay doi
        return existing.getRecordCount() != group.records.size()
                || !existing.getEndTime().equals(group.endTime);
    }

    private SessionDto toDto(SessionEntity entity) {
        SessionDto dto = new SessionDto();
        dto.setSessionId(entity.getSessionId());
        dto.setStartTime(entity.getStartTime());
        dto.setEndTime(entity.getEndTime());
        dto.setRecordCount(entity.getRecordCount());
        dto.setLabel(entity.getLabel());
        dto.setAvgBpm(entity.getAvgBpm());
        dto.setAvgSpo2(entity.getAvgSpo2());
        dto.setAvgBodyTemp(entity.getAvgBodyTemp());
        dto.setAvgGsrAdc(entity.getAvgGsrAdc());
        dto.setActive(entity.isActive());
        dto.setRecords(null); // chi metadata, khong ke records
        return dto;
    }

    private SessionDto toDtoWithRecords(SessionEntity entity) {
        SessionDto dto = toDto(entity);

        // Doc lai records tu final_result thuoc phiên nay
        Instant start = entity.getStartTime();
        Instant end = entity.getEndTime();

        Query query = new Query(
                new org.springframework.data.mongodb.core.query.Criteria("ingested_at").gte(start).lte(end)
        ).with(Sort.by(Sort.Direction.ASC, "ingested_at"));

        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        List<SessionDto.HealthRecordDto> records = docs.stream()
                .map(this::docToRecord)
                .toList();

        dto.setRecords(records);
        return dto;
    }

    private SessionDto.HealthRecordDto docToRecord(Document doc) {
        SessionDto.HealthRecordDto record = new SessionDto.HealthRecordDto();
        record.setId(doc.getObjectId("_id") != null ? doc.getObjectId("_id").toHexString() : null);
        record.setBpm(toDouble(doc.get("bpm")));
        record.setSpo2(toDouble(doc.get("spo2")));
        record.setBodyTemp(toDouble(doc.get("body_temp")));
        record.setGsrAdc(toDouble(doc.get("gsr_adc")));
        record.setExtTempC(toDouble(doc.get("room_temp")));
        record.setExtHumidityPct(toDouble(doc.get("humidity")));
        record.setLabel(doc.getString("label"));
        record.setConfidence(toDouble(doc.get("confidence")));
        record.setIngestedAt(parseIngestedAt(doc.get("ingested_at")));
        // timestamp: try raw string field first, fallback to ingestedAt
        String tsStr = doc.getString("timestamp");
        if (tsStr != null && !tsStr.isBlank()) {
            try {
                // ESP32 gửi giờ UTC+7 → parse rồi gắn offset +7 để ra UTC
                LocalDateTime ldt = LocalDateTime.parse(tsStr, TS_PARSE_FMT);
                record.setTimestamp(ldt.toInstant(VN_ZONE));
            } catch (Exception e) {
                record.setTimestamp(record.getIngestedAt());
            }
        } else {
            record.setTimestamp(record.getIngestedAt());
        }
        return record;
    }

    private Double toDouble(Object value) {
        if (value == null) return null;
        if (value instanceof Double d) return d;
        if (value instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    // ================================================================
    // Inner class: Nhom ban ghi theo phiên
    // ================================================================
    private static class SessionGroup {
        final String sessionId;
        final Instant startTime;
        Instant endTime;
        final List<Document> records = new ArrayList<>();

        SessionGroup(String sessionId, Instant startTime) {
            this.sessionId = sessionId;
            this.startTime = startTime;
            this.endTime = startTime;
        }

        void addRecord(Document doc) {
            Instant ingestedAt = parseInstant(doc.get("ingested_at"));
            records.add(doc);
            if (ingestedAt.isAfter(endTime)) {
                endTime = ingestedAt;
            }
        }

        Instant parseInstant(Object value) {
            if (value == null) return Instant.now();
            if (value instanceof java.util.Date date) return date.toInstant();
            if (value instanceof Instant i) return i;
            if (value instanceof LocalDateTime ldt) return ldt.toInstant(ZoneOffset.UTC);
            try { return Instant.parse(value.toString()); }
            catch (Exception e) {
                try {
                    // ESP32 format "yyyy:MM:dd - HH:mm:ss" → parse as UTC+7
                    LocalDateTime ldt = LocalDateTime.parse(value.toString(), TS_PARSE_FMT);
                    return ldt.toInstant(VN_ZONE);
                } catch (Exception ex) {
                    return Instant.now();
                }
            }
        }

        Double computeAvg(String field) {
            List<Double> values = records.stream()
                    .map(doc -> {
                        Object v = doc.get(field);
                        if (v == null) return null;
                        if (v instanceof Number n) return n.doubleValue();
                        try { return Double.parseDouble(v.toString()); }
                        catch (Exception e) { return null; }
                    })
                    .filter(Objects::nonNull)
                    .toList();
            if (values.isEmpty()) return null;
            return values.stream().mapToDouble(d -> d).average().orElse(Double.NaN);
        }

        String computeModeLabel() {
            Map<String, Long> counts = records.stream()
                    .map(doc -> doc.getString("label"))
                    .filter(Objects::nonNull)
                    .collect(Collectors.groupingBy(l -> l, Collectors.counting()));
            if (counts.isEmpty()) return null;
            return counts.entrySet().stream()
                    .max(Map.Entry.comparingByValue())
                    .map(Map.Entry::getKey)
                    .orElse(null);
        }
    }
}
