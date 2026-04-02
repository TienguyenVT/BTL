package com.iomt.dashboard.components.health;

import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
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

/**
 * Controller: Du lieu suc khoe (Dashboard + Lich su).
 * Doc truc tiep tu MongoDB collection "final_result", tra JSON cho Frontend.
 *
 * Base path: /api/health
 *
 * ENDPOINTS:
 *    GET /api/health/latest   — Chi so moi nhat (Dashboard)
 *    GET /api/health/history  — Du lieu N gio gan day
 *    GET /api/health/recent   — N ban ghi gan nhat
 *
 * Chu y: He thong KHONG phan chia theo user/device.
 *        Lay HET data tu final_result de hien thi.
 */
@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
public class HealthController {

    private static final Logger log = LoggerFactory.getLogger(HealthController.class);
    private static final String LOG_FILE = "C:\\Documents\\BTL\\debug-db097a.log";
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS");
    private static final DateTimeFormatter TS_PARSE_FMT = DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss");

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

    // ================================================================
    // GET /api/health/latest
    //    Lay chi so moi nhat (khong loc theo user/device).
    //    Output: Map<String, Object> | null
    // ================================================================
    @GetMapping("/latest")
    public Map<String, Object> getLatest(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        writeLog("initial", "H1", "HealthController.getLatest:enter",
                "getLatest called, no user/device filter",
                Map.of("rawUserId", userId != null ? userId : "null"));

        // H1 FIX: Query all data from final_result, no user/device filter
        Query query = new Query()
                .with(Sort.by(Sort.Direction.DESC, "ingested_at"))
                .limit(1);

        writeLog("initial", "H1", "HealthController.getLatest:beforeFindOne",
                "querying final_result (all data, sorted by ingested_at DESC)",
                Map.of("collection", "final_result", "sortField", "ingested_at"));

        Document doc = mongoTemplate.findOne(query, Document.class, "final_result");

        writeLog("initial", "H1", "HealthController.getLatest:afterFindOne",
                "findOne result",
                Map.of("docFound", doc != null,
                        "docKeys", doc != null ? new ArrayList<>(doc.keySet()) : Collections.emptyList(),
                        "rawDoc", doc != null ? doc.entrySet().stream()
                                .collect(java.util.stream.Collectors.toMap(
                                        Map.Entry::getKey, e -> e.getValue() instanceof org.bson.types.ObjectId
                                                ? e.getValue().toString() : e.getValue()))
                                : Collections.emptyMap()));

        if (doc == null) {
            writeLog("initial", "H1", "HealthController.getLatest:docNull",
                    "final_result is empty",
                    Map.of());
            return null;
        }

        Map<String, Object> result = flattenDocument(doc);

        writeLog("initial", "H1", "HealthController.getLatest:result",
                "returning health data",
                Map.of("resultFields", new ArrayList<>(result.keySet()), "result", result));

        return result;
    }

    // ================================================================
    // GET /api/health/history
    //    Lay du lieu trong khoang N gio.
    //    Neu khong co data trong khoang N gio, tra ve TAT CA data (demo data).
    //    Output: List<Map<String, Object>> (tu cu den moi)
    // ================================================================
    @GetMapping("/history")
    public List<Map<String, Object>> getHistory(
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestParam(defaultValue = "24") int hours) {

        writeLog("initial", "H2", "HealthController.getHistory:enter",
                "getHistory called, no user/device filter",
                Map.of("hours", hours));

        // H2 FIX: Use ingested_at (datetime) instead of timestamp (string)
        // ingested_at is datetime.datetime in MongoDB, which compares correctly with Instant
        Instant timeAgo = Instant.now().minus(hours, ChronoUnit.HOURS);

        writeLog("initial", "H2", "HealthController.getHistory:query",
                "time range for query using ingested_at (datetime)",
                Map.of("hours", hours, "timeAgo", timeAgo.toString(), "now", Instant.now().toString()));

        // Query using ingested_at (datetime) >= Instant — this type-matches correctly
        Query query = new Query(
                Criteria.where("ingested_at").gte(timeAgo)
        ).with(Sort.by(Sort.Direction.ASC, "ingested_at"));

        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        writeLog("initial", "H2", "HealthController.getHistory:afterFind",
                "history query result",
                Map.of("hours", hours, "docCount", docs.size()));

        // Neu khong co data trong khoang N gio, lay TAT CA data (demo data)
        if (docs.isEmpty()) {
            writeLog("initial", "H2", "HealthController.getHistory:fallback",
                    "no data in time range, falling back to all data",
                    Map.of("hours", hours));

            Query allQuery = new Query()
                    .with(Sort.by(Sort.Direction.ASC, "ingested_at"));
            docs = mongoTemplate.find(allQuery, Document.class, "final_result");

            writeLog("initial", "H2", "HealthController.getHistory:fallbackResult",
                    "all data fallback",
                    Map.of("totalDocs", docs.size()));
        }

        return docs.stream().map(this::flattenDocument).toList();
    }

    // ================================================================
    // GET /api/health/recent
    //    Lay N ban ghi gan nhat (khong loc theo user/device).
    //    Output: List<Map<String, Object>>
    // ================================================================
    @GetMapping("/recent")
    public List<Map<String, Object>> getRecent(
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestParam(defaultValue = "20") int limit) {

        writeLog("initial", "H1", "HealthController.getRecent:enter",
                "getRecent called, no user/device filter",
                Map.of("limit", limit));

        // H1 FIX: Query all data from final_result, no device filter
        Query query = new Query()
                .with(Sort.by(Sort.Direction.DESC, "ingested_at"))
                .limit(limit);

        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        writeLog("initial", "H1", "HealthController.getRecent:afterFind",
                "recent query result",
                Map.of("limit", limit, "docCount", docs.size()));

        return docs.stream().map(this::flattenDocument).toList();
    }

    // ================================================================
    // GET /api/health/environment
    //    Lay du lieu moi nhat tu datalake_raw: nhiet do phong + do am.
    //    Cap nhat realtime 1s.
    //    Output: Map with extTempC, extHumidityPct, timestamp
    // ================================================================
    @GetMapping("/environment")
    public Map<String, Object> getEnvironment() {
        // Lay ban ghi moi nhat tu datalake_raw
        Query query = new Query()
                .with(Sort.by(Sort.Direction.DESC, "ingested_at"))
                .limit(1);

        Document doc = mongoTemplate.findOne(query, Document.class, "datalake_raw");

        if (doc == null) {
            return Map.of(
                    "extTempC", (Double) null,
                    "extHumidityPct", (Double) null,
                    "timestamp", (Long) null
            );
        }

        // Fields are inside "sensor" subdocument
        Document sensor = doc.get("sensor", Document.class);
        Double roomTemp = sensor != null ? toDouble(sensor.get("dht11_room_temp")) : null;
        Double humidity = sensor != null ? toDouble(sensor.get("dht11_humidity")) : null;

        return Map.of(
                "extTempC", roomTemp,
                "extHumidityPct", humidity,
                "timestamp", datetimeToEpochMs(doc.get("ingested_at"))
        );
    }

    // ================================================================
    // Tra ve danh sach device_id trong final_result (cho FE hien thi)
    // ================================================================
    @GetMapping("/devices")
    public List<Map<String, Object>> getAvailableDevices() {
        // Tra ve distinct device_ids tu final_result
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

    // ================================================================
    // Helper: Chuyen Document thanh Map thuan tien cho FE
    // ================================================================
    private Map<String, Object> flattenDocument(Document doc) {
        Map<String, Object> map = new LinkedHashMap<>();

        // _id -> id
        if (doc.getObjectId("_id") != null) {
            map.put("id", doc.getObjectId("_id").toHexString());
        }

        // Fields
        map.put("deviceId", doc.getString("device_id"));
        map.put("bpm", toDouble(doc.get("bpm")));
        map.put("spo2", toDouble(doc.get("spo2")));
        map.put("bodyTemp", toDouble(doc.get("body_temp")));
        map.put("gsrAdc", toDouble(doc.get("gsr_adc")));
        map.put("label", doc.getString("label"));
        map.put("confidence", toDouble(doc.get("confidence")));

        // DHT11 fields
        map.put("extTempC", toDouble(doc.get("room_temp")));
        map.put("extHumidityPct", toDouble(doc.get("humidity")));

        // Time slot
        map.put("timeSlot", doc.getString("time_slot"));

        // Metadata
        map.put("source", doc.getString("source"));
        map.put("dataQuality", doc.getString("data_quality"));

        // ingested_at: convert to ISO-8601 string for FE to parse
        Object ingestedAt = doc.get("ingested_at");
        if (ingestedAt != null) {
            // ingested_at is a datetime.datetime in MongoDB
            // Convert to ISO-8601 epoch millis so FE can use new Date(timestamp)
            long epochMs = datetimeToEpochMs(ingestedAt);
            map.put("timestamp", epochMs);
            map.put("ingestedAt", ingestedAt.toString());
        } else {
            // Fallback: try parsing the string timestamp field
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

    /**
     * Convert MongoDB datetime (java.util.Date or datetime.datetime) to epoch milliseconds.
     * This is what FE expects: new Date(epochMs) -> valid Date object.
     */
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
        // Fallback: try parsing string representation
        if (value != null) {
            try {
                return Instant.parse(value.toString()).toEpochMilli();
            } catch (Exception e) {
                log.warn("Could not parse ingested_at: {}", value);
            }
        }
        return 0L;
    }

    /**
     * Parse string timestamp "yyyy:MM:dd - HH:mm:ss" to epoch milliseconds.
     * Input example: "2026:03:31 - 15:55:20"
     */
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
