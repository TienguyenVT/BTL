package com.iomt.dashboard.components.health;

import com.iomt.dashboard.components.device.DeviceEntity;
import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.bson.types.ObjectId;
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

@Service
@RequiredArgsConstructor
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);

    private static final long SESSION_GAP_MS = 5 * 60 * 1000L;

    private static final ZoneOffset VN_ZONE = ZoneOffset.ofHours(7);

    private static final DateTimeFormatter TS_PARSE_FMT = DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss");

    private final MongoTemplate mongoTemplate;

    private List<String> getUserDeviceMacs(String userId) {
        if (userId == null || userId.isBlank()) {
            return List.of();
        }
        Query query = new Query(Criteria.where("user_id").is(userId));
        List<DeviceEntity> devices = mongoTemplate.find(query, DeviceEntity.class, "devices");
        return devices.stream()
                .map(d -> d.getMacAddress())
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(m -> !m.isBlank())
                .map(String::toUpperCase)
                .toList();
    }

    public List<SessionDto> getAllSessions(String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return List.of();
        }

        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> allEntities = mongoTemplate.find(query, SessionEntity.class, "sessions");

        Map<String, String> macToName = buildMacToNameMap();

        return allEntities.stream()
                .map(entity -> {
                    List<Document> relatedDocs = findSessionRecords(entity, userMacs);
                    if (relatedDocs.isEmpty()) return null;
                    SessionDto dto = toDto(entity);
                    dto.setRecordCount(relatedDocs.size());
                    String firstMac = relatedDocs.get(0).getString("mac_address");
                    dto.setDeviceId(findDeviceIdByMac(userMacs, firstMac));
                    dto.setDeviceName(macToName.get(firstMac));
                    return dto;
                })
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }

    public List<SessionDto> getSessionsInRange(int hours, String userId, String deviceId) {
        List<String> resolvedMacs;
        String resolvedName = null;

        if (deviceId != null && !deviceId.isBlank()) {
            DeviceEntity device = mongoTemplate.findOne(
                    new Query(new Criteria("_id").is(new ObjectId(deviceId))),
                    DeviceEntity.class, "devices");
            if (device == null || !userId.equals(device.getUserId())) {
                return List.of();
            }
            String mac = device.getMacAddress();
            resolvedMacs = mac != null && !mac.isBlank() ? List.of(mac.trim().toUpperCase()) : List.of();
            resolvedName = device.getName();
        } else {
            resolvedMacs = getUserDeviceMacs(userId);
        }

        if (resolvedMacs.isEmpty()) {
            return List.of();
        }

        Instant timeAgo = Instant.now().minus(hours, ChronoUnit.HOURS);
        Query query = new Query(
                Criteria.where("start_time").gte(timeAgo)
        ).with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> allEntities = mongoTemplate.find(query, SessionEntity.class, "sessions");

        final List<String> macs = resolvedMacs;
        final String name = resolvedName;
        return allEntities.stream()
                .filter(entity -> {
                    List<Document> relatedDocs = findSessionRecords(entity, macs);
                    return !relatedDocs.isEmpty();
                })
                .map(entity -> {
                    SessionDto dto = toDto(entity);
                    dto.setRecordCount((int) findSessionRecords(entity, macs).size());
                    dto.setDeviceId(deviceId);
                    dto.setDeviceName(name);
                    return dto;
                })
                .collect(Collectors.toList());
    }

    public SessionDto getLatestActiveSession(String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return null;
        }

        Query query = new Query(
                Criteria.where("active").is(true)
        ).with(Sort.by(Sort.Direction.DESC, "start_time"));
        List<SessionEntity> activeEntities = mongoTemplate.find(query, SessionEntity.class, "sessions");

        for (SessionEntity entity : activeEntities) {
            List<Document> relatedDocs = findSessionRecords(entity, userMacs);
            if (!relatedDocs.isEmpty()) {
                SessionDto dto = toDto(entity);
                dto.setRecordCount(relatedDocs.size());
                dto.setRecords(relatedDocs.stream().map(this::docToRecord).collect(Collectors.toList()));
                return dto;
            }
        }
        return null;
    }

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

    private static final String[] SESSION_PROJECTION_FIELDS = {
            "_id", "timestamp", "ingested_at", "mac_address",
            "bpm", "spo2", "body_temp", "gsr_adc",
            "room_temp", "humidity", "label", "confidence"
    };

    public SessionDto getLiveSession(String userId, String deviceId) {
        List<String> targetMacs;

        if (deviceId != null && !deviceId.isBlank()) {
            DeviceEntity device = mongoTemplate.findOne(
                    new Query(new Criteria("_id").is(new ObjectId(deviceId))),
                    DeviceEntity.class, "devices");
            if (device == null || !userId.equals(device.getUserId())) {
                return null;
            }
            String mac = device.getMacAddress();
            targetMacs = mac != null && !mac.isBlank() ? List.of(mac.trim().toUpperCase()) : List.of();
        } else {
            targetMacs = getUserDeviceMacs(userId);
        }

        if (targetMacs.isEmpty()) {
            return null;
        }

        Instant now = Instant.now();

        Query latestQuery = projection(
                new Query(
                        Criteria.where("mac_address").in(targetMacs)
                ).with(Sort.by(Sort.Direction.DESC, "timestamp"))
                        .limit(1),
                SESSION_PROJECTION_FIELDS);
        Document latestDoc = mongoTemplate.findOne(latestQuery, Document.class, "final_result");

        if (latestDoc == null) {
            return null;
        }

        Instant latestTs = parseTimestamp(latestDoc.get("timestamp"));

        boolean isActive = Math.abs(now.toEpochMilli() - latestTs.toEpochMilli()) < SESSION_GAP_MS;

        if (!isActive) {
            return null;
        }

        Instant sessionStart = latestTs.minus(SESSION_GAP_MS, ChronoUnit.MILLIS);

        LocalDateTime sessionStartVn = LocalDateTime.ofInstant(sessionStart, VN_ZONE);
        String sessionStartStr = sessionStartVn.format(TS_PARSE_FMT);

        Query recordsQuery = projection(
                new Query(
                        Criteria.where("timestamp").gte(sessionStartStr)
                                .and("mac_address").in(targetMacs)
                ).with(Sort.by(Sort.Direction.ASC, "timestamp")),
                SESSION_PROJECTION_FIELDS);

        List<Document> docs = mongoTemplate.find(recordsQuery, Document.class, "final_result");

        if (docs.isEmpty()) {
            return null;
        }

        Instant actualStart = parseTimestamp(docs.get(0).get("timestamp"));
        Instant actualEnd = parseTimestamp(docs.get(docs.size() - 1).get("timestamp"));

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

    public SessionDto getSessionById(String sessionId) {
        Query query = new Query(
                new Criteria("session_id").is(sessionId)
        );
        SessionEntity entity = mongoTemplate.findOne(query, SessionEntity.class, "sessions");
        if (entity == null) {
            return null;
        }
        return toDtoWithRecords(entity);
    }

    public SessionDto getSessionById(String sessionId, String userId) {
        List<String> userMacs = getUserDeviceMacs(userId);
        if (userMacs.isEmpty()) {
            return null;
        }

        Query query = new Query(
                new Criteria("session_id").is(sessionId)
        );
        SessionEntity entity = mongoTemplate.findOne(query, SessionEntity.class, "sessions");
        if (entity == null) {
            return null;
        }

        List<Document> relatedDocs = findSessionRecords(entity, userMacs);
        if (relatedDocs.isEmpty()) {
            return null;
        }

        SessionDto dto = toDto(entity);
        dto.setRecordCount(relatedDocs.size());
        dto.setRecords(relatedDocs.stream().map(this::docToRecord).collect(Collectors.toList()));
        return dto;
    }

    private static final String[] REBUILD_PROJECTION_FIELDS = {
            "_id", "timestamp", "mac_address",
            "bpm", "spo2", "body_temp", "gsr_adc", "label",
            "device_id", "ingested_at"
    };
    private static Query projection(Query q, String... fields) {
        q.fields().include("_id");
        for (String f : fields) { q.fields().include(f); }
        return q;
    }

    public void rebuildSessions() {
        log.info("[SessionService] Starting session rebuild...");

        Query query = projection(
                new Query()
                        .with(Sort.by(Sort.Direction.ASC, "timestamp")),
                REBUILD_PROJECTION_FIELDS);
        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        if (docs.isEmpty()) {
            log.info("[SessionService] final_result is empty, no sessions to build.");
            mongoTemplate.remove(new Query(), SessionEntity.class, "sessions");
            return;
        }

        List<SessionGroup> groups = detectSessions(docs);
        log.info("[SessionService] Detected {} sessions from {} records.", groups.size(), docs.size());

        Instant now = Instant.now();

        mongoTemplate.remove(new Query(), SessionEntity.class, "sessions");
        log.info("[SessionService] Cleared old sessions.");

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

    private List<SessionGroup> detectSessions(List<Document> docs) {
        List<SessionGroup> groups = new ArrayList<>();
        SessionGroup current = null;

        for (Document doc : docs) {
            Instant ts = parseTimestamp(doc.get("timestamp"));

            if (current == null) {
                current = new SessionGroup(deriveSessionId(doc), ts);
            } else if (Math.abs(ts.toEpochMilli() - current.endTime.toEpochMilli()) > SESSION_GAP_MS) {
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

    private Instant parseTimestamp(Object value) {
        if (value == null) {
            return parseIngestedAt(null);
        }
        if (value instanceof Number n) {
            return Instant.ofEpochMilli(n.longValue());
        }
        try {
            String s = value.toString().trim();
            try {
                LocalDateTime ldt = LocalDateTime.parse(s, TS_PARSE_FMT);
                return ldt.toInstant(VN_ZONE);
            } catch (Exception e) {
                return Instant.ofEpochMilli(Long.parseLong(s));
            }
        } catch (Exception e) {
            log.warn("[SessionService] Could not parse timestamp '{}', fallback to ingested_at", value);
            return parseIngestedAt(null);
        }
    }

    private Instant parseIngestedAt(Object value) {
        if (value == null) return Instant.now();
        if (value instanceof java.util.Date date) return date.toInstant();
        if (value instanceof Instant instant) return instant;
        if (value instanceof LocalDateTime ldt) return ldt.toInstant(ZoneOffset.UTC);
        try {
            return Instant.parse(value.toString());
        } catch (Exception e) {
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
                new Query(new Criteria("session_id").is(sessionId)),
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
        dto.setRecords(null);
        return dto;
    }

    private SessionDto toDtoWithRecords(SessionEntity entity) {
        return toDtoWithRecords(entity, List.of());
    }

    private SessionDto toDtoWithRecords(SessionEntity entity, List<String> userMacs) {
        SessionDto dto = toDto(entity);

        Instant startUtc = entity.getStartTime();
        Instant endUtc = entity.getEndTime();

        LocalDateTime startVn = LocalDateTime.ofInstant(startUtc, VN_ZONE);
        LocalDateTime endVn = LocalDateTime.ofInstant(endUtc, VN_ZONE);

        String startTsStr = startVn.format(TS_PARSE_FMT);
        String endTsStr = endVn.format(TS_PARSE_FMT);

        Criteria timeCriteria = new Criteria("timestamp").gte(startTsStr).lte(endTsStr);

        if (!userMacs.isEmpty()) {
            timeCriteria = timeCriteria.and("mac_address").in(userMacs);
        }

        Query query = projection(
                new Query(timeCriteria)
                        .with(Sort.by(Sort.Direction.ASC, "timestamp")),
                SESSION_PROJECTION_FIELDS);

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

        String tsStr = doc.getString("timestamp");
        if (tsStr != null && !tsStr.isBlank()) {
            try {
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

    private Map<String, String> buildMacToNameMap() {
        Query query = new Query();
        List<DeviceEntity> devices = mongoTemplate.find(query, DeviceEntity.class, "devices");
        Map<String, String> map = new HashMap<>();
        for (DeviceEntity d : devices) {
            if (d.getMacAddress() != null && d.getName() != null) {
                map.put(d.getMacAddress().trim().toUpperCase(), d.getName());
            }
        }
        return map;
    }

    private String findDeviceIdByMac(List<String> userMacs, String mac) {
        String upperMac = mac != null ? mac.toUpperCase() : null;
        Query query = new Query(Criteria.where("mac_address").is(upperMac));
        DeviceEntity device = mongoTemplate.findOne(query, DeviceEntity.class, "devices");
        return device != null ? device.getId() : null;
    }

    private static final String[] RECORD_FIELDS = {
            "_id", "timestamp", "ingested_at", "mac_address",
            "bpm", "spo2", "body_temp", "gsr_adc",
            "room_temp", "humidity", "label", "confidence"
    };

    public FeverStressRecordDto getFeverStressRecords(String userId, String deviceId, int page, int size, int hours) {
        List<String> targetMacs;

        if (deviceId != null && !deviceId.isBlank()) {
            DeviceEntity device = mongoTemplate.findOne(
                    new Query(new Criteria("_id").is(new ObjectId(deviceId))),
                    DeviceEntity.class, "devices");
            if (device == null || !userId.equals(device.getUserId())) {
                return emptyPage(page, size);
            }
            String mac = device.getMacAddress();
            targetMacs = mac != null && !mac.isBlank() ? List.of(mac.trim().toUpperCase()) : List.of();
        } else {
            targetMacs = getUserDeviceMacs(userId);
        }

        if (targetMacs.isEmpty()) {
            return emptyPage(page, size);
        }

        Instant since = Instant.now().minus(hours, ChronoUnit.HOURS);
        LocalDateTime sinceVn = LocalDateTime.ofInstant(since, VN_ZONE);
        String sinceStr = sinceVn.format(TS_PARSE_FMT);

        Query countQuery = new Query(
                Criteria.where("timestamp").gte(sinceStr)
                        .and("mac_address").in(targetMacs)
                        .and("label").in("Stress", "Fever")
        );
        long total = mongoTemplate.count(countQuery, Document.class, "final_result");

        if (total == 0) {
            return emptyPage(page, size);
        }

        int totalPages = (int) Math.ceil((double) total / size);
        int skip = page * size;

        Query query = new Query(
                Criteria.where("timestamp").gte(sinceStr)
                        .and("mac_address").in(targetMacs)
                        .and("label").in("Stress", "Fever")
        ).with(Sort.by(Sort.Direction.DESC, "timestamp"))
                .skip(skip)
                .limit(size);

        Query projected = projection(query, RECORD_FIELDS);
        List<Document> docs = mongoTemplate.find(projected, Document.class, "final_result");

        List<SessionDto.HealthRecordDto> records = docs.stream()
                .map(this::docToRecord)
                .toList();

        for (int i = 0; i < records.size(); i++) {
            SessionDto.HealthRecordDto rec = records.get(i);
            if (rec.getId() == null) {
                rec.setId(docs.get(i).getString("timestamp") + "|" +
                           docs.get(i).getString("mac_address") + "|" +
                           docs.get(i).getString("label"));
            }
        }

        FeverStressRecordDto dto = new FeverStressRecordDto();
        dto.setTotalCount(total);
        dto.setPage(page);
        dto.setSize(size);
        dto.setTotalPages(totalPages);
        dto.setRecords(records);

        return dto;
    }

    private FeverStressRecordDto emptyPage(int page, int size) {
        int totalPages = 0;
        return new FeverStressRecordDto(List.of(), 0, page, size, 0);
    }

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

        Instant parseInstant(Object value) {
            if (value == null) return Instant.now();
            if (value instanceof Number n) {
                return Instant.ofEpochMilli(n.longValue());
            }
            String s = value.toString().trim();
            try {
                LocalDateTime ldt = LocalDateTime.parse(s, DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss"));
                return ldt.toInstant(ZoneOffset.ofHours(7));
            } catch (Exception e) {
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
