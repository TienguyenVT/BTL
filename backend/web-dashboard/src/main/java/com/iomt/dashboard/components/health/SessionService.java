package com.iomt.dashboard.components.health;

import com.iomt.dashboard.components.device.DeviceEntity;
import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
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
 * 1. Doc ALL records tu final_result, sort theo timestamp ASC (thoi gian ESP32 do)
 * 2. Quet lan luot: neu 2 ban ghi cach nhau > 1 phut → phiên mới
 * 3. Moi phiên: tinh avg, label chinh (mode cua predicted_label)
 * 4. active = (hieu thoi gian tu ban ghi cuoi cung den hien tai < 1 phut)
 * 5. LUU: chi save/update phiên moi hoac phiên active
 *
 * Chú ý: Dùng trường "timestamp" (thời gian ESP32 đo) thay vì "ingested_at"
 * (thời gian server nhận) để tránh fragmentation do network delay.
 */
@Service
@RequiredArgsConstructor
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);

    /** Khoảng gap (ms) de nhan biet phiên mới: 1 phút */
    private static final long SESSION_GAP_MS = 60 * 1000L;

    /** ESP32 gửi timestamp ở múi giờ Việt Nam UTC+7 */
    private static final ZoneOffset VN_ZONE = ZoneOffset.ofHours(7);

    /** DateTimeFormatter parse chuoi "yyyy:MM:dd - HH:mm:ss" */
    private static final DateTimeFormatter TS_PARSE_FMT = DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss");

    private final MongoTemplate mongoTemplate;

    /**
     * Lay danh sach MAC cua thiet bi ma user da dang ky.
     */
    private List<String> getUserDeviceMacs(String userId) {
        if (userId == null || userId.isBlank()) {
            return List.of();
        }
        Query query = new Query(Criteria.where("user_id").is(userId));
        List<DeviceEntity> devices = mongoTemplate.find(query, DeviceEntity.class, "devices");
        return devices.stream()
                .map(d -> d.getMacAddress() != null ? d.getMacAddress().toLowerCase() : null)
                .filter(Objects::nonNull)
                .toList();
    }

    // ================================================================
    // Public API
    // ================================================================

    /**
     * Tra ve danh sach TAT CA phiên đo, sap xep theo startTime DESC.
     * Chi tra ve session ma co ban ghi thuoc device cua user.
     */
    public List<SessionDto> getAllSessions(String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return List.of();
        }

        // Lay sessions co it nhat 1 ban ghi thuoc user devices
        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> allEntities = mongoTemplate.find(query, SessionEntity.class, "sessions");

        // Loc chi nhung session co mac thuoc user
        return allEntities.stream()
                .filter(entity -> {
                    // Kiem tra session co ban ghi thuoc user devices khong
                    List<Document> relatedDocs = findSessionRecords(entity, userMacs);
                    return !relatedDocs.isEmpty();
                })
                .map(entity -> {
                    SessionDto dto = toDto(entity);
                    // Chi lay nhung ban ghi thuoc user devices
                    dto.setRecordCount((int) findSessionRecords(entity, userMacs).size());
                    return dto;
                })
                .collect(Collectors.toList());
    }

    /**
     * Tra ve danh sach phiên trong khoang N gio gan day.
     * Chi tra ve session co ban ghi thuoc device cua user.
     */
    public List<SessionDto> getSessionsInRange(int hours, String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return List.of();
        }

        Instant timeAgo = Instant.now().minus(hours, ChronoUnit.HOURS);
        Query query = new Query(
                Criteria.where("start_time").gte(timeAgo)
        ).with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> allEntities = mongoTemplate.find(query, SessionEntity.class, "sessions");

        return allEntities.stream()
                .filter(entity -> {
                    List<Document> relatedDocs = findSessionRecords(entity, userMacs);
                    return !relatedDocs.isEmpty();
                })
                .map(entity -> {
                    SessionDto dto = toDto(entity);
                    dto.setRecordCount((int) findSessionRecords(entity, userMacs).size());
                    return dto;
                })
                .collect(Collectors.toList());
    }

    /**
     * Tra ve PHIEN ACTIVE cuoi cung (dang theo doi, chua bi ngat).
     * Chi tra ve session cua user devices.
     */
    public SessionDto getLatestActiveSession(String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return null;
        }

        Query query = new Query(
                Criteria.where("active").is(true)
        ).with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> activeEntities = mongoTemplate.find(query, SessionEntity.class, "sessions");

        // Tim session active co ban ghi thuoc user devices
        for (SessionEntity entity : activeEntities) {
            List<Document> relatedDocs = findSessionRecords(entity, userMacs);
            if (!relatedDocs.isEmpty()) {
                SessionDto dto = toDto(entity);
                dto.setRecordCount(relatedDocs.size());
                // Them records chi tiet
                dto.setRecords(relatedDocs.stream().map(this::docToRecord).collect(Collectors.toList()));
                return dto;
            }
        }
        return null;
    }

    /**
     * Lay cac ban ghi cua session chi thuoc user devices.
     */
    private List<Document> findSessionRecords(SessionEntity entity, List<String> userMacs) {
        Instant startUtc = entity.getStartTime();
        Instant endUtc = entity.getEndTime();

        LocalDateTime startVn = LocalDateTime.ofInstant(startUtc, VN_ZONE);
        LocalDateTime endVn = LocalDateTime.ofInstant(endUtc, VN_ZONE);

        String startTsStr = startVn.format(TS_PARSE_FMT);
        String endTsStr = endVn.format(TS_PARSE_FMT);

        Query query = new Query(
                Criteria.where("timestamp").gte(startTsStr).lte(endTsStr)
                        .and("mac_address").in(userMacs)
        ).with(Sort.by(Sort.Direction.ASC, "timestamp"));

        return mongoTemplate.find(query, Document.class, "final_result");
    }

    /**
     * Tra ve session active — query TRỰC TIẾP final_result mà không qua sessions collection.
     * Chi tra ve session thuoc user devices.
     */
    public SessionDto getLiveSession(String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return null;
        }

        Instant now = Instant.now();

        // Lay 1 ban ghi moi nhat thuoc user devices
        Query latestQuery = new Query(
                Criteria.where("mac_address").in(userMacs)
        ).with(Sort.by(Sort.Direction.DESC, "timestamp")).limit(1);
        Document latestDoc = mongoTemplate.findOne(latestQuery, Document.class, "final_result");

        if (latestDoc == null) {
            return null;
        }

        Instant latestTs = parseTimestamp(latestDoc.get("timestamp"));

        // Xac dinh session active: (now - latestTs) < 1 phut
        boolean isActive = Math.abs(now.toEpochMilli() - latestTs.toEpochMilli()) < SESSION_GAP_MS;

        if (!isActive) {
            return null;
        }

        // Lay ALL records cua session active thuoc user devices
        Instant sessionStart = latestTs.minus(SESSION_GAP_MS, ChronoUnit.MILLIS);
        Query recordsQuery = new Query(
                Criteria.where("timestamp").gte(sessionStart)
                        .and("mac_address").in(userMacs)
        ).with(Sort.by(Sort.Direction.ASC, "timestamp"));

        List<Document> docs = mongoTemplate.find(recordsQuery, Document.class, "final_result");

        if (docs.isEmpty()) {
            return null;
        }

        // Xac dinh chinh xac start/end cua session
        Instant actualStart = parseTimestamp(docs.get(0).get("timestamp"));
        Instant actualEnd = parseTimestamp(docs.get(docs.size() - 1).get("timestamp"));

        // Loc nhung record thuc su thuoc session
        List<Document> sessionDocs = new ArrayList<>();
        Instant currentSessionStart = actualStart;
        for (Document doc : docs) {
            Instant docTime = parseTimestamp(doc.get("timestamp"));
            if (Math.abs(docTime.toEpochMilli() - currentSessionStart.toEpochMilli()) > SESSION_GAP_MS) {
                break;
            }
            sessionDocs.add(doc);
            if (docTime.isAfter(currentSessionStart)) {
                currentSessionStart = docTime;
            }
        }

        // Build SessionDto
        SessionDto dto = new SessionDto();
        dto.setSessionId("live-" + latestTs.toEpochMilli());
        dto.setStartTime(sessionDocs.isEmpty() ? actualStart : parseTimestamp(sessionDocs.get(0).get("timestamp")));
        dto.setEndTime(sessionDocs.isEmpty() ? actualEnd : parseTimestamp(sessionDocs.get(sessionDocs.size() - 1).get("timestamp")));
        dto.setRecordCount(sessionDocs.size());
        dto.setActive(true);

        dto.setAvgBpm(computeAvg(sessionDocs, "bpm"));
        dto.setAvgSpo2(computeAvg(sessionDocs, "spo2"));
        dto.setAvgBodyTemp(computeAvg(sessionDocs, "body_temp"));
        dto.setAvgGsrAdc(computeAvg(sessionDocs, "gsr_adc"));
        dto.setLabel(computeModeLabel(sessionDocs));

        List<SessionDto.HealthRecordDto> records = sessionDocs.stream()
                .map(this::docToRecord)
                .collect(Collectors.toList());
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

    /**
     * Tra ve chi tiet 1 phiên (kem danh sach records) chi thuoc user devices.
     */
    public SessionDto getSessionById(String sessionId, String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return null;
        }

        Query query = new Query(
                new org.springframework.data.mongodb.core.query.Criteria("session_id").is(sessionId)
        );
        SessionEntity entity = mongoTemplate.findOne(query, SessionEntity.class, "sessions");
        if (entity == null) {
            return null;
        }

        // Lay ban ghi chi thuoc user devices
        List<Document> relatedDocs = findSessionRecords(entity, userMacs);
        if (relatedDocs.isEmpty()) {
            return null;
        }

        SessionDto dto = toDto(entity);
        dto.setRecordCount(relatedDocs.size());
        dto.setRecords(relatedDocs.stream().map(this::docToRecord).collect(Collectors.toList()));
        return dto;
    }

    // ================================================================
    // Session Rebuild (goi tu Scheduler)
    // ================================================================

    /**
     * Quet toan bo final_result, phat hien phiên moi / cap nhat phiên active,
     * LUU ket qua vao bang sessions.
     *
     * Chay moi 30 giay (tu SessionScheduler).
     *
     * Strategy: Xoa toan bo sessions cu, tao lai tu dau.
     * Vi moi detectSessions() tao UUID ngau nhien, nen khong the
     * match sessions cu vs moi -> chi can insert all.
     */
    public void rebuildSessions() {
        log.info("[SessionService] Starting session rebuild...");

        // 1. Doc ALL records tu final_result, sort ASC theo timestamp (thoi gian ESP32 do)
        Query query = new Query().with(Sort.by(Sort.Direction.ASC, "timestamp"));
        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        if (docs.isEmpty()) {
            log.info("[SessionService] final_result is empty, no sessions to build.");
            // Xoa sessions cu neu final_result trong
            mongoTemplate.remove(new Query(), SessionEntity.class, "sessions");
            return;
        }

        // 2. Phat hien phiên bang cach gap > 1 phut
        List<SessionGroup> groups = detectSessions(docs);
        log.info("[SessionService] Detected {} sessions from {} records.", groups.size(), docs.size());

        Instant now = Instant.now();

        // 3. Xoa toan bo sessions cu
        mongoTemplate.remove(new Query(), SessionEntity.class, "sessions");
        log.info("[SessionService] Cleared old sessions.");

        // 4. Insert all new sessions
        for (SessionGroup group : groups) {
            Instant lastRecordTime = group.endTime;
            boolean isActive = Math.abs(now.toEpochMilli() - lastRecordTime.toEpochMilli()) < SESSION_GAP_MS;
            SessionEntity entity = buildEntity(group, isActive);
            mongoTemplate.insert(entity, "sessions");
        }

        log.info("[SessionService] Session rebuild complete. Inserted {} sessions. Active: {}",
                groups.size(),
                groups.stream().filter(g -> Math.abs(now.toEpochMilli() - g.endTime.toEpochMilli()) < SESSION_GAP_MS).count());
    }

    // ================================================================
    // Private helpers
    // ================================================================

    /**
     * Phat hien cac phiên tu danh sach documents.
     * Gap > 1 phut giua 2 ban ghi lien tiep (theo timestamp) → phiên mới.
     * Session ID cố định: hash MD5(first_record_timestamp + first_record_device_id).
     */
    private List<SessionGroup> detectSessions(List<Document> docs) {
        List<SessionGroup> groups = new ArrayList<>();
        SessionGroup current = null;

        for (Document doc : docs) {
            Instant ts = parseTimestamp(doc.get("timestamp"));

            if (current == null) {
                current = new SessionGroup(deriveSessionId(doc), ts);
            } else if (Math.abs(ts.toEpochMilli() - current.endTime.toEpochMilli()) > SESSION_GAP_MS) {
                // Gap > 1 phut → kết thúc phiên hiện tại, bắt đầu phiên mới
                groups.add(current);
                current = new SessionGroup(deriveSessionId(doc), ts);
            }

            current.addRecord(doc);
        }

        if (current != null) {
            groups.add(current);
        }

        return groups;
    }

    /**
     * Tao session ID cố định từ data thực tế của bản ghi đầu tiên trong phiên.
     * Không dùng UUID.randomUUID() vì sẽ tạo ID mới mỗi lần rebuild → frontend 404.
     */
    private String deriveSessionId(Document firstRecord) {
        String ts = firstRecord.getString("timestamp");
        if (ts == null) {
            Object ingested = firstRecord.get("ingested_at");
            ts = ingested != null ? ingested.toString() : UUID.randomUUID().toString();
        }
        String deviceId = firstRecord.getString("device_id");
        String key = (ts != null ? ts : "") + "|" + (deviceId != null ? deviceId : "");
        return UUID.nameUUIDFromBytes(key.getBytes()).toString();
    }

    /**
     * Parse trường timestamp (thời gian ESP32 gửi, Unix ms hoặc string).
     * Fallback sang ingested_at nếu timestamp null.
     */
    private Instant parseTimestamp(Object value) {
        if (value == null) {
            return parseIngestedAt(null); // fallback
        }
        // Unix milliseconds
        if (value instanceof Number n) {
            return Instant.ofEpochMilli(n.longValue());
        }
        // String parse
        try {
            String s = value.toString().trim();
            // ESP32 format: "yyyy:MM:dd - HH:mm:ss"
            try {
                LocalDateTime ldt = LocalDateTime.parse(s, TS_PARSE_FMT);
                return ldt.toInstant(VN_ZONE);
            } catch (Exception e) {
                // Unix ms string
                return Instant.ofEpochMilli(Long.parseLong(s));
            }
        } catch (Exception e) {
            log.warn("[SessionService] Could not parse timestamp '{}', fallback to ingested_at", value);
            return parseIngestedAt(null);
        }
    }

    /** Parse ingested_at (java.util.Date / Instant / LocalDateTime / String) — chỉ dùng khi timestamp null */
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
        return toDtoWithRecords(entity, List.of());
    }

    /**
     * Tra ve chi tiet 1 phiên (kem danh sach records) chi thuoc user devices.
     */
    private SessionDto toDtoWithRecords(SessionEntity entity, List<String> userMacs) {
        SessionDto dto = toDto(entity);

        // Query final_result bang trường timestamp (String "yyyy:MM:dd - HH:mm:ss").
        // timestamp là UTC+7, format này sort lexicographically = chronological order.
        // Dùng [firstTs, lastTs] để bao trùm toàn bộ phiên.
        Instant startUtc = entity.getStartTime();
        Instant endUtc = entity.getEndTime();

        // Chuyển UTC → UTC+7 để khớp với ESP32 timestamp
        LocalDateTime startVn = LocalDateTime.ofInstant(startUtc, VN_ZONE);
        LocalDateTime endVn = LocalDateTime.ofInstant(endUtc, VN_ZONE);

        String startTsStr = startVn.format(TS_PARSE_FMT);
        String endTsStr = endVn.format(TS_PARSE_FMT);

        // Loc theo MAC neu co userMacs
        org.springframework.data.mongodb.core.query.Criteria timeCriteria =
                new org.springframework.data.mongodb.core.query.Criteria("timestamp")
                        .gte(startTsStr)
                        .lte(endTsStr);

        if (!userMacs.isEmpty()) {
            timeCriteria = timeCriteria.and("mac_address").in(userMacs);
        }

        Query query = new Query(timeCriteria)
                .with(Sort.by(Sort.Direction.ASC, "timestamp"));

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
        record.setMacAddress(doc.getString("mac_address"));
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
            Instant ts = parseInstant(doc.get("timestamp"));
            records.add(doc);
            if (ts.isAfter(endTime)) {
                endTime = ts;
            }
        }

        /**
         * Parse trường timestamp (ESP32 device time).
         * Supports: Number (Unix ms), String (Unix ms or "yyyy:MM:dd - HH:mm:ss").
         */
        Instant parseInstant(Object value) {
            if (value == null) return Instant.now();
            if (value instanceof Number n) {
                return Instant.ofEpochMilli(n.longValue());
            }
            String s = value.toString().trim();
            // ESP32 format "yyyy:MM:dd - HH:mm:ss" → parse as UTC+7
            try {
                LocalDateTime ldt = LocalDateTime.parse(s, TS_PARSE_FMT);
                return ldt.toInstant(VN_ZONE);
            } catch (Exception e) {
                // Fallback: Unix ms string
                try {
                    return Instant.ofEpochMilli(Long.parseLong(s));
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
