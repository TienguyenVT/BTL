package com.iomt.dashboard.components.dashboard;

/**
 * ============================================================
 * DashboardController — REST Controller: Bang dieu khien
 * ============================================================
 *
 * BASE PATH: /api/dashboard
 * SECURITY:  Protected (can JWT)
 *
 * ENDPOINTS:
 *
 *    GET /api/dashboard
 *       Lay chi so moi nhat cua user.
 *       OUTPUT: 200 + DashboardDto | 200 (null, chua co du lieu)
 *
 *    GET /api/dashboard/{id}
 *       Lay chi tiet 1 ban ghi.
 *       OUTPUT: 200 + DashboardDto | 404
 *
 * RESPONSE (DashboardDto):
 *    {
 *        "id": "65f...",
 *        "bpm": 72.5,
 *        "spo2": 98.2,
 *        "bodyTemp": 36.8,
 *        "gsrAdc": 512.0,
 *        "label": "Normal",
 *        "timestamp": "2026-03-23T10:00:00Z"
 *    }
 */
public class DashboardController {

    // ----------------------------------------------------------
    // GET /api/dashboard
    //    @GetMapping
    //    public ResponseEntity<DashboardDto> getLatest() {
    //        return ResponseEntity.ok(dashboardService.getLatest(getCurrentUserId()));
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // GET /api/dashboard/{id}
    //    @GetMapping("/{id}")
    //    public ResponseEntity<DashboardDto> getById(@PathVariable String id) {
    //        return ResponseEntity.ok(dashboardService.getById(id, getCurrentUserId()));
    //    }
    // ----------------------------------------------------------
}
