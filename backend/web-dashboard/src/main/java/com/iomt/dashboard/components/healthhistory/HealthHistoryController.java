package com.iomt.dashboard.components.healthhistory;

/**
 * ============================================================
 * HealthHistoryController — REST Controller: Lich su suc khoe
 * ============================================================
 *
 * BASE PATH: /api/health-history
 * SECURITY:  Protected (can JWT)
 *
 * ENDPOINT:
 *
 *    GET /api/health-history
 *       Lay lich su suc khoe (phan trang, loc theo ngay).
 *       QUERY PARAMS:
 *          - page : so trang (0-based, mac dinh: 0)
 *          - size : so ban ghi / trang (mac dinh: 20)
 *          - date : loc theo ngay (yyyy-MM-dd, optional)
 *       OUTPUT: 200 + Page<HealthHistoryDto>
 *
 *    VI DU:
 *       GET /api/health-history?page=0&size=20
 *       GET /api/health-history?date=2026-03-23
 *       GET /api/health-history?page=1&size=10&date=2026-03-23
 *
 *    RESPONSE (Page<HealthHistoryDto>):
 *       {
 *           "content": [
 *               { "id": "...", "bpm": 72.5, "timestamp": "...", ... },
 *               ...
 *           ],
 *           "page": 0,
 *           "size": 20,
 *           "totalElements": 150,
 *           "totalPages": 8
 *       }
 *
 * CAC BUOC TRIEN KHAI:
 *    1. Doc @RequestParam page, size, date
 *    2. Goi healthHistoryService.getHistory(...) hoac getHistoryByDate(...)
 *    3. Tra ve ResponseEntity.ok(result)
 */
public class HealthHistoryController {

    // ----------------------------------------------------------
    // GET /api/health-history
    //    @GetMapping
    //    public ResponseEntity<Page<HealthHistoryDto>> getHistory(
    //            @RequestParam(defaultValue = "0") int page,
    //            @RequestParam(defaultValue = "20") int size,
    //            @RequestParam(required = false) @DateTimeFormat(iso = DATE) LocalDate date) {
    //        Page<HealthHistoryDto> result = (date == null)
    //            ? healthHistoryService.getHistory(getCurrentUserId(), page, size)
    //            : healthHistoryService.getHistoryByDate(getCurrentUserId(), date, page, size);
    //        return ResponseEntity.ok(result);
    //    }
    // ----------------------------------------------------------
}
