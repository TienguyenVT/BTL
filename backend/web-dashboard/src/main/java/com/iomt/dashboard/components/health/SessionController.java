package com.iomt.dashboard.components.health;

import com.iomt.dashboard.common.UserUtils;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/health/sessions")
@RequiredArgsConstructor
public class SessionController {

    private static final Logger log = LoggerFactory.getLogger(SessionController.class);

    private final SessionService sessionService;

    @GetMapping
    public ResponseEntity<List<SessionDto>> getAllSessions(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        List<SessionDto> sessions = sessionService.getAllSessions(uid);
        return ResponseEntity.ok(sessions);
    }

    @GetMapping("/latest")
    public ResponseEntity<SessionDto> getLatestActiveSession(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        SessionDto session = sessionService.getLatestActiveSession(uid);
        if (session == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(session);
    }

    @GetMapping("/{sessionId}")
    public ResponseEntity<SessionDto> getSessionById(
            @PathVariable String sessionId,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        SessionDto session = sessionService.getSessionById(sessionId, uid);
        if (session == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(session);
    }

    @GetMapping("/history")
    public ResponseEntity<List<SessionDto>> getSessionsInRange(
            @RequestParam(defaultValue = "168") int hours,
            @RequestParam(required = false) String deviceId,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        List<SessionDto> sessions = sessionService.getSessionsInRange(hours, uid, deviceId);
        return ResponseEntity.ok(sessions);
    }

    @GetMapping("/live")
    public ResponseEntity<SessionDto> getLiveSession(
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestParam(required = false) String deviceId) {
        String uid = UserUtils.extractUserId(userId);
        SessionDto session = sessionService.getLiveSession(uid, deviceId);
        if (session == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(session);
    }

    @GetMapping("/fever-stress-records")
    public ResponseEntity<FeverStressRecordDto> getFeverStressRecords(
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestParam(required = false) String deviceId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "8760") int hours) {

        String uid = UserUtils.extractUserId(userId);
        FeverStressRecordDto result = sessionService.getFeverStressRecords(uid, deviceId, page, size, hours);
        return ResponseEntity.ok(result);
    }
}
