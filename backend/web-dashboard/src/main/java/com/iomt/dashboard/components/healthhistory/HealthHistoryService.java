package com.iomt.dashboard.components.healthhistory;

/**
 * ============================================================
 * HealthHistoryService — Service: Lich su suc khoe (doc, phan trang)
 * ============================================================
 *
 * REUSE: DashboardEntity (cung cau truc du lieu)
 *
 * NGHIEP VU:
 *    - getHistory(userId, page, size)      : Lay lich su (phan trang)
 *    - getHistoryByDate(userId, date, ...) : Lay lich su theo ngay
 *
 * getHistory(userId, page, size):
 *    1. Tao Pageable (page, size, sort timestamp desc)
 *    2. Query: findByUserIdOrderByTimestampDesc(userId, pageable)
 *    3. Chuyen thanh Page<HealthHistoryDto>
 *    4. Tra ve
 *
 * getHistoryByDate(userId, date, page, size):
 *    1. Tinh startOfDay, endOfDay tu date
 *    2. Tao Pageable
 *    3. Query: findByUserIdAndTimestampBetween(..., start, end, pageable)
 *    4. Tra ve Page<HealthHistoryDto>
 *
 * LY DO TUYET DOI KHONG SUA / XOA:
 *    Du lieu y te khong duoc thay doi de dam bao tinh toan ven.
 */
public class HealthHistoryService {

    // ----------------------------------------------------------
    // getHistory(String userId, int page, int size)
    //    INPUT : userId, page (0-based), size
    //    OUTPUT: Page<HealthHistoryDto>
    //    - PageRequest.of(page, size, Sort.by("timestamp").descending())
    //    - dashboardEntityRepository.findByUserIdOrderByTimestampDesc(userId, pageable)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // getHistoryByDate(String userId, LocalDate date, int page, int size)
    //    INPUT : userId, date, page, size
    //    OUTPUT: Page<HealthHistoryDto>
    //    - Instant start = date.atStartOfDay(ZoneOffset.UTC).toInstant()
    //    - Instant end = start.plus(1, ChronoUnit.DAYS)
    //    - dashboardEntityRepository.findByUserIdAndTimestampBetween(...)
    // ----------------------------------------------------------
}
