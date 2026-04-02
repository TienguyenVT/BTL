package com.iomt.dashboard.components.health;

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
 *    GET /api/health/sessions           — Danh sach tat ca sessions
 *    GET /api/health/sessions/latest     — Session active cuoi cung (cho Dashboard)
 *    GET /api/health/sessions/{id}      — Chi tiet 1 session + records
 *    GET /api/health/sessions/history   — Sessions trong khoang N gio
 *
 * Khong loc theo user/device — tra tat ca sessions.
 */
@RestController
@RequestMapping("/api/health/sessions")
@RequiredArgsConstructor
public class SessionController {

    private static final Logger log = LoggerFactory.getLogger(SessionController.class);

    private final SessionService sessionService;

    // ================================================================
    // GET /api/health/sessions
    //    Tra ve danh sach tat ca phiên đo (metadata, khong ke records).
    // ================================================================
    @GetMapping
    public ResponseEntity<List<SessionDto>> getAllSessions() {
        List<SessionDto> sessions = sessionService.getAllSessions();
        return ResponseEntity.ok(sessions);
    }

    // ================================================================
    // GET /api/health/sessions/latest
    //    Tra ve phiên active cuoi cung (kem records) — cho Dashboard.
    //    Neu khong co phiên active nao, tra ve 204 No Content.
    // ================================================================
    @GetMapping("/latest")
    public ResponseEntity<SessionDto> getLatestActiveSession() {
        SessionDto session = sessionService.getLatestActiveSession();
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
    public ResponseEntity<SessionDto> getSessionById(@PathVariable String sessionId) {
        SessionDto session = sessionService.getSessionById(sessionId);
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
            @RequestParam(defaultValue = "168") int hours) {
        List<SessionDto> sessions = sessionService.getSessionsInRange(hours);
        return ResponseEntity.ok(sessions);
    }

    // ================================================================
    // GET /api/health/sessions/live
    //    Tra ve session active — query TRỰC TIẾP final_result, không qua rebuild.
    //    Fixes race condition: frontend poll không phụ thuộc rebuild timing.
    //    Neu khong co session active, tra ve 204 No Content.
    // ================================================================
    @GetMapping("/live")
    public ResponseEntity<SessionDto> getLiveSession() {
        SessionDto session = sessionService.getLiveSession();
        if (session == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(session);
    }
}
