package com.iomt.dashboard.components.health;

import com.iomt.dashboard.common.UserUtils;
import com.iomt.dashboard.components.device.DeviceEntity;
import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;

@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
public class HealthController {

    private static final Logger log = LoggerFactory.getLogger(HealthController.class);
    private static final String LOG_FILE = "C:\\Documents\\BTL\\debug-db097a.log";
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS");
    private static final DateTimeFormatter TS_PARSE_FMT = DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss");
    private static final String DEVICES_COLL = "devices";

    private final MongoTemplate mongoTemplate;

    private void writeLog(String runId, String hypothesisId, String location, String message, Map<String, Object> data) {
        try (PrintWriter pw = new PrintWriter(new FileWriter(LOG_FILE, true))) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("sessionId", "db097a");
            entry.put("id", "log_" + System.currentTimeMillis() + "_" + Math.abs(message.hashCode()));
            entry.put("timestamp", System.currentTimeMillis());
            entry.put("runId", runId);
            entry.put("hypothesisId", hypothesisId);
            entry.put("location", location);
            entry.put("message", message);
            entry.put("data", data);
            entry.put("_ts", LocalDateTime.now().format(FMT));
            pw.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(entry));
        } catch (IOException e) {
            log.error("DEBUG LOG WRITE FAILED", e);
        }
    }

    private List<String> getUserDeviceMacs(String userId) {
        if (userId == null || userId.isBlank()) {
            return List.of();
        }
        Query query = new Query(Criteria.where("user_id").is(userId));
        List<DeviceEntity> devices = mongoTemplate.find(query, DeviceEntity.class, DEVICES_COLL);
        return devices.stream()
                .map(d -> d.getMacAddress() != null ? d.getMacAddress().trim().toUpperCase() : null)
                .filter(Objects::nonNull)
                .toList();
    }

    @GetMapping("/latest")
    public ResponseEntity<Map<String, Object>> getLatest(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        List<String> userMacs = getUserDeviceMacs(uid);

        writeLog("mac-filter", "H1", "HealthController.getLatest:enter",
                "getLatest with MAC filter",
                Map.of("userId", uid, "userMacs", userMacs));

        if (userMacs.isEmpty()) {
            writeLog("mac-filter", "H1", "HealthController.getLatest:noDevices",
                    "user has no registered devices",
                    Map.of());
            return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
        }

        Query query = new Query(
                Criteria.where("mac_address").in(userMacs)
        ).with(Sort.by(Sort.Direction.DESC, "ingested_at")).limit(1);

        writeLog("mac-filter", "H1", "HealthController.getLatest:beforeFindOne",
                "querying final_result with MAC filter",
                Map.of("macs", userMacs));

        Document doc = mongoTemplate.findOne(query, Document.class, "final_result");

        if (doc == null) {
            writeLog("mac-filter", "H1", "HealthController.getLatest:docNull",
                    "no data found for user's devices",
                    Map.of());
            return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
        }

        Map<String, Object> result = flattenDocument(doc);
        writeLog("mac-filter", "H1", "HealthController.getLatest:result",
                "returning health data",
                Map.of("macAddress", doc.getString("mac_address"), "bpm", result.get("bpm")));

        return ResponseEntity.ok(result);
    }

    @GetMapping("/history")
    public ResponseEntity<List<Map<String, Object>>> getHistory(
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestParam(defaultValue = "24") int hours) {

        String uid = UserUtils.extractUserId(userId);
        List<String> userMacs = getUserDeviceMacs(uid);

        writeLog("mac-filter", "H2", "HealthController.getHistory:enter",
                "getHistory with MAC filter",
                Map.of("userId", uid, "hours", hours, "userMacs", userMacs));

        if (userMacs.isEmpty()) {
            writeLog("mac-filter", "H2", "HealthController.getHistory:noDevices",
                    "user has no registered devices",
                    Map.of());
            return ResponseEntity.ok(List.of());
        }

        Instant timeAgo = Instant.now().minus(hours, ChronoUnit.HOURS);

        Query query = new Query(
                Criteria.where("mac_address").in(userMacs)
                        .and("ingested_at").gte(timeAgo)
        ).with(Sort.by(Sort.Direction.ASC, "ingested_at"));

        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        writeLog("mac-filter", "H2", "HealthController.getHistory:result",
                "history query result",
                Map.of("docCount", docs.size()));

        return ResponseEntity.ok(docs.stream().map(this::flattenDocument).toList());
    }

    @GetMapping("/recent")
    public ResponseEntity<List<Map<String, Object>>> getRecent(
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestParam(defaultValue = "20") int limit) {

        String uid = UserUtils.extractUserId(userId);
        List<String> userMacs = getUserDeviceMacs(uid);

        writeLog("mac-filter", "H1", "HealthController.getRecent:enter",
                "getRecent with MAC filter",
                Map.of("userId", uid, "limit", limit, "userMacs", userMacs));

        if (userMacs.isEmpty()) {
            writeLog("mac-filter", "H1", "HealthController.getRecent:noDevices",
                    "user has no registered devices",
                    Map.of());
            return ResponseEntity.ok(List.of());
        }

        Query query = new Query(
                Criteria.where("mac_address").in(userMacs)
        ).with(Sort.by(Sort.Direction.DESC, "ingested_at")).limit(limit);

        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        writeLog("mac-filter", "H1", "HealthController.getRecent:result",
                "recent query result",
                Map.of("docCount", docs.size()));

        return ResponseEntity.ok(docs.stream().map(this::flattenDocument).toList());
    }

    @GetMapping("/environment")
    public Map<String, Object> getEnvironment() {
        Query query = new Query()
                .with(Sort.by(Sort.Direction.DESC, "ingested_at"))
                .limit(1);

        Document doc = mongoTemplate.findOne(query, Document.class, "datalake_raw");

        java.util.Map<String, Object> result = new java.util.HashMap<>();
        if (doc == null) {
            result.put("extTempC", null);
            result.put("extHumidityPct", null);
            result.put("timestamp", null);
            return result;
        }

        Document sensor = doc.get("sensor", Document.class);
        Double roomTemp = sensor != null ? toDouble(sensor.get("dht11_room_temp")) : null;
        Double humidity = sensor != null ? toDouble(sensor.get("dht11_humidity")) : null;

        result.put("extTempC", roomTemp);
        result.put("extHumidityPct", humidity);
        result.put("timestamp", datetimeToEpochMs(doc.get("ingested_at")));
        return result;
    }

    @GetMapping("/devices")
    public List<Map<String, Object>> getAvailableDevices() {
        List<Document> distinct = mongoTemplate.findAll(Document.class, "final_result");
        Set<String> seen = new LinkedHashSet<>();
        List<Map<String, Object>> result = new ArrayList<>();
        for (Document d : distinct) {
            String deviceId = d.getString("device_id");
            if (deviceId != null && seen.add(deviceId)) {
                result.add(Map.of(
                        "deviceId", deviceId,
                        "source", d.getString("source") != null ? d.getString("source") : "",
                        "dataQuality", d.getString("data_quality") != null ? d.getString("data_quality") : ""
                ));
            }
        }

        writeLog("initial", "H1", "HealthController.getAvailableDevices",
                "distinct device_ids from final_result",
                Map.of("deviceCount", result.size(), "devices", result));
        return result;
    }

    private Map<String, Object> flattenDocument(Document doc) {
        Map<String, Object> map = new LinkedHashMap<>();

        if (doc.getObjectId("_id") != null) {
            map.put("id", doc.getObjectId("_id").toHexString());
        }

        map.put("deviceId", doc.getString("device_id"));
        map.put("bpm", toDouble(doc.get("bpm")));
        map.put("spo2", toDouble(doc.get("spo2")));
        map.put("bodyTemp", toDouble(doc.get("body_temp")));
        map.put("gsrAdc", toDouble(doc.get("gsr_adc")));
        map.put("label", doc.getString("label"));
        map.put("confidence", toDouble(doc.get("confidence")));

        map.put("extTempC", toDouble(doc.get("room_temp")));
        map.put("extHumidityPct", toDouble(doc.get("humidity")));

        map.put("timeSlot", doc.getString("time_slot"));

        map.put("source", doc.getString("source"));
        map.put("dataQuality", doc.getString("data_quality"));
        map.put("macAddress", doc.getString("mac_address"));

        Object ingestedAt = doc.get("ingested_at");
        if (ingestedAt != null) {
            long epochMs = datetimeToEpochMs(ingestedAt);
            map.put("timestamp", epochMs);
            map.put("ingestedAt", ingestedAt.toString());
        } else {
            String ts = doc.getString("timestamp");
            if (ts != null && !ts.isBlank()) {
                Long parsed = parseStringTimestamp(ts);
                if (parsed != null) {
                    map.put("timestamp", parsed);
                } else {
                    map.put("timestamp", null);
                }
            } else {
                map.put("timestamp", null);
            }
        }

        writeLog("initial", "H5", "HealthController.flattenDocument",
                "flattened values",
                Map.of("rawBpm", doc.get("bpm"), "rawSpo2", doc.get("spo2"),
                        "rawBodyTemp", doc.get("body_temp"), "rawGsrAdc", doc.get("gsr_adc"),
                        "rawLabel", doc.get("label"),
                        "convertedBpm", map.get("bpm"), "convertedSpo2", map.get("spo2"),
                        "convertedBodyTemp", map.get("bodyTemp"), "convertedGsrAdc", map.get("gsrAdc"),
                        "outputTimestamp", map.get("timestamp")));

        return map;
    }

    private Double toDouble(Object value) {
        if (value == null) return null;
        if (value instanceof Double) return (Double) value;
        if (value instanceof Number) return ((Number) value).doubleValue();
        try {
            return Double.parseDouble(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private long datetimeToEpochMs(Object value) {
        if (value instanceof java.util.Date date) {
            return date.getTime();
        }
        if (value instanceof java.time.Instant instant) {
            return instant.toEpochMilli();
        }
        if (value instanceof java.time.LocalDateTime ldt) {
            return ldt.toInstant(ZoneOffset.UTC).toEpochMilli();
        }
        if (value != null) {
            try {
                return Instant.parse(value.toString()).toEpochMilli();
            } catch (Exception e) {
                log.warn("Could not parse ingested_at: {}", value);
            }
        }
        return 0L;
    }

    private Long parseStringTimestamp(String ts) {
        try {
            LocalDateTime ldt = LocalDateTime.parse(ts, TS_PARSE_FMT);
            return ldt.toInstant(ZoneOffset.UTC).toEpochMilli();
        } catch (Exception e) {
            log.warn("Could not parse timestamp string '{}': {}", ts, e.getMessage());
            return null;
        }
    }
}
