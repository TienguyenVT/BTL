package com.iomt.dashboard.components.health;

import com.iomt.dashboard.common.UserUtils;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Controller: Phiên đo (Session) — quản lý và truy vấn phiên đo.
 *
 * Base path: /api/health/sessions
 *
 * ENDPOINTS:
 *    GET /api/health/sessions           — Danh sach sessions cua user
 *    GET /api/health/sessions/latest     — Session active cuoi cung (cho Dashboard)
 *    GET /api/health/sessions/{id}      — Chi tiet 1 session + records
 *    GET /api/health/sessions/history   — Sessions trong khoang N gio
 *
 * Cac endpoint loc data theo MAC cua user da dang ky trong bang devices.
 */
@RestController
@RequestMapping("/api/health/sessions")
@RequiredArgsConstructor
public class SessionController {

    private static final Logger log = LoggerFactory.getLogger(SessionController.class);

    private final SessionService sessionService;

    // ================================================================
    // GET /api/health/sessions
    //    Tra ve danh sach tat ca phiên đo cua user (metadata, khong ke records).
    // ================================================================
    @GetMapping
    public ResponseEntity<List<SessionDto>> getAllSessions(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        List<SessionDto> sessions = sessionService.getAllSessions(uid);
        return ResponseEntity.ok(sessions);
    }

    // ================================================================
    // GET /api/health/sessions/latest
    //    Tra ve phiên active cuoi cung (kem records) — cho Dashboard.
    //    Neu khong co phiên active nao, tra ve 204 No Content.
    // ================================================================
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

    // ================================================================
    // GET /api/health/sessions/{id}
    //    Tra ve chi tiet 1 phiên (kem danh sach records day du).
    // ================================================================
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

    // ================================================================
    // GET /api/health/sessions/history?hours=168
    //    Tra ve sessions trong khoang N gio (default 168 = 7 ngay).
    // ================================================================
    @GetMapping("/history")
    public ResponseEntity<List<SessionDto>> getSessionsInRange(
            @RequestParam(defaultValue = "168") int hours,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        List<SessionDto> sessions = sessionService.getSessionsInRange(hours, uid);
        return ResponseEntity.ok(sessions);
    }

    // ================================================================
    // GET /api/health/sessions/live
    //    Tra ve session active — query TRỰC TIẾP final_result, không qua rebuild.
    //    Neu khong co session active, tra ve 204 No Content.
    // ================================================================
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
}
