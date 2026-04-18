package com.iomt.dashboard.components.alert;

import com.iomt.dashboard.components.device.DeviceEntity;
import com.iomt.dashboard.components.health.SessionEntity;
import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AlertService {

    private static final Logger log = LoggerFactory.getLogger(AlertService.class);

    private static final String SESSION_COLLECTION = "sessions";
    private static final String DEVICES_COLLECTION = "devices";
    private static final String ALERTS_COLLECTION = "alerts";

    private static final ZoneOffset VN_ZONE = ZoneOffset.ofHours(7);
    private static final DateTimeFormatter TS_PARSE_FMT = DateTimeFormatter.ofPattern("yyyy:MM:dd - HH:mm:ss");

    private static final long DEBOUNCE_MS = 5 * 60 * 1000L;

    private final MongoTemplate mongoTemplate;

    public void checkAndCreateAlerts() {
        log.info("[AlertService] Checking sessions for Stress/Fever alerts...");

        Instant now = Instant.now();
        Instant windowStart = now.minusSeconds(DEBOUNCE_MS / 1000 * 2);

        List<SessionEntity> recentSessions = findRecentSessions(windowStart);

        if (recentSessions.isEmpty()) {
            log.info("[AlertService] No recent sessions found.");
            return;
        }

        int created = 0;
        for (SessionEntity session : recentSessions) {
            String label = session.getLabel();
            if (label == null || (!label.equals("Stress") && !label.equals("Fever"))) {
                continue;
            }

            if (isDuplicateAlert(session, now)) {
                log.debug("[AlertService] Skipping duplicate alert for session {} label={}",
                        session.getSessionId(), label);
                continue;
            }

            String userId = resolveUserId(session);
            if (userId == null) {
                log.warn("[AlertService] Cannot resolve userId for session {} — skipping alert",
                        session.getSessionId());
                continue;
            }

            AlertEntity alert = buildAlert(session, userId, label);
            mongoTemplate.insert(alert, ALERTS_COLLECTION);
            log.info("[AlertService] Created alert: label={} sessionId={} userId={}",
                    label, session.getSessionId(), userId);
            created++;
        }

        log.info("[AlertService] Alert check complete. Created {} new alerts.", created);
    }

    private List<SessionEntity> findRecentSessions(Instant since) {
        Query query = new Query(
                Criteria.where("updated_at").gte(since)
                        .and("label").in("Stress", "Fever")
        );
        return mongoTemplate.find(query, SessionEntity.class, SESSION_COLLECTION);
    }

    private boolean isDuplicateAlert(SessionEntity session, Instant now) {
        Instant window = now.minusMillis(DEBOUNCE_MS);
        Query query = new Query(
                Criteria.where("timestamp").gte(window)
                        .and("label").is(session.getLabel())
                        .and("mac_address").is(resolveMac(session))
        );
        return mongoTemplate.exists(query, ALERTS_COLLECTION);
    }

    private String resolveUserId(SessionEntity session) {
        List<String> macs = extractMacs(session);
        if (macs.isEmpty()) return null;

        String mac = macs.get(0);
        String upperMac = mac != null ? mac.toUpperCase() : null;
        DeviceEntity device = mongoTemplate.findOne(
                new Query(Criteria.where("mac_address").is(upperMac)),
                DeviceEntity.class, DEVICES_COLLECTION
        );
        return device != null ? device.getUserId() : null;
    }

    private List<String> extractMacs(SessionEntity session) {
        Instant startUtc = session.getStartTime();
        Instant endUtc = session.getEndTime();

        LocalDateTime startVn = LocalDateTime.ofInstant(startUtc, VN_ZONE);
        LocalDateTime endVn = LocalDateTime.ofInstant(endUtc, VN_ZONE);

        String startStr = startVn.format(TS_PARSE_FMT);
        String endStr = endVn.format(TS_PARSE_FMT);

        Query query = new Query(
                Criteria.where("timestamp").gte(startStr).lte(endStr)
        );
        query.fields().include("mac_address");

        List<Document> docs = mongoTemplate.find(query, Document.class, "final_result");

        return docs.stream()
                .map(doc -> doc.getString("mac_address"))
                .filter(Objects::nonNull)
                .map(String::toUpperCase)
                .distinct()
                .collect(Collectors.toList());
    }

    private String resolveMac(SessionEntity session) {
        List<String> macs = extractMacs(session);
        return macs.isEmpty() ? null : macs.get(0);
    }

    private AlertEntity buildAlert(SessionEntity session, String userId, String label) {
        String mac = resolveMac(session);

        AlertEntity alert = new AlertEntity();
        alert.setUserId(userId);
        alert.setLabel(label);
        alert.setTimestamp(Instant.now());
        alert.setIsRead(false);
        alert.setMacAddress(mac);

        alert.setBpm(session.getAvgBpm());
        alert.setSpo2(session.getAvgSpo2());
        alert.setBodyTemp(session.getAvgBodyTemp());
        alert.setGsrAdc(session.getAvgGsrAdc());

        alert.setMessage(buildMessage(label, session));

        return alert;
    }

    private String buildMessage(String label, SessionEntity session) {
        if ("Fever".equals(label)) {
            String temp = session.getAvgBodyTemp() != null
                    ? String.format("%.1f°C", session.getAvgBodyTemp())
                    : "N/A";
            return String.format(
                    "Nhiet do co the cao: %s (BPM trung binh: %s, SpO2: %s).",
                    temp,
                    session.getAvgBpm() != null ? String.format("%.0f", session.getAvgBpm()) : "N/A",
                    session.getAvgSpo2() != null ? String.format("%.1f%%", session.getAvgSpo2()) : "N/A"
            );
        } else {
            return String.format(
                    "Stress: GSR trung binh %.0f, BPM trung binh %s, SpO2 %s.",
                    session.getAvgGsrAdc() != null ? session.getAvgGsrAdc() : 0,
                    session.getAvgBpm() != null ? String.format("%.0f", session.getAvgBpm()) : "N/A",
                    session.getAvgSpo2() != null ? String.format("%.1f%%", session.getAvgSpo2()) : "N/A"
            );
        }
    }
}
