package com.iomt.dashboard.components.alert;

/**
 * ============================================================
 * AlertController — REST Controller: Quan ly canh bao
 * ============================================================
 *
 * BASE PATH: /api/alerts
 * SECURITY:  Protected (can JWT)
 *
 * ENDPOINTS:
 *
 *    GET /api/alerts
 *       Lay danh sach canh bao.
 *       OUTPUT: 200 + List<AlertDto>
 *
 *    GET /api/alerts/count
 *       Dem so canh bao chua doc.
 *       OUTPUT: 200 + { "unreadCount": 3 }
 *
 *    DELETE /api/alerts/{id}
 *       Xoa canh bao.
 *       OUTPUT: 204 | 404
 *
 * RESPONSE (AlertDto):
 *    {
 *        "id": "65f...",
 *        "label": "Stress",
 *        "message": "Phat hien trang thai Stress luc 10:00",
 *        "timestamp": "2026-03-23T10:00:00Z",
 *        "isRead": false
 *    }
 */
public class AlertController {

    // ----------------------------------------------------------
    // GET /api/alerts
    //    @GetMapping
    //    public ResponseEntity<List<AlertDto>> getAll() {
    //        return ResponseEntity.ok(alertService.getAll(getCurrentUserId()));
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // GET /api/alerts/count
    //    @GetMapping("/count")
    //    public ResponseEntity<Map<String, Long>> getUnreadCount() {
    //        long count = alertService.getUnreadCount(getCurrentUserId());
    //        return ResponseEntity.ok(Map.of("unreadCount", count));
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // DELETE /api/alerts/{id}
    //    @DeleteMapping("/{id}")
    //    public ResponseEntity<Void> delete(@PathVariable String id) {
    //        alertService.delete(id, getCurrentUserId());
    //        return ResponseEntity.noContent().build();
    //    }
    // ----------------------------------------------------------
}
