package com.iomt.dashboard.components.dashboard;

/**
 * ============================================================
 * DashboardService — Service: Lay chi so moi nhat
 * ============================================================
 *
 * NGHIEP VU:
 *    - getLatest(userId)   : Lay ban ghi moi nhat
 *    - getById(id, userId) : Lay 1 ban ghi theo id
 *
 * getLatest(userId):
 *    1. Tim ban ghi co timestamp lon nhat theo userId
 *    2. Tra ve DashboardDto
 *    3. Neu khong co du lieu -> tra ve null (Frontend xu ly)
 *
 * getById(id, userId):
 *    1. Tim ban ghi theo id + userId
 *    2. Tra ve DashboardDto
 *    3. Neu khong tim thay -> 404
 */
public class DashboardService {

    // ----------------------------------------------------------
    // getLatest(String userId)
    //    INPUT : userId
    //    OUTPUT: DashboardDto | null
    //    - findTopByUserIdOrderByTimestampDesc(userId)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // getById(String id, String userId)
    //    INPUT : id, userId
    //    OUTPUT: DashboardDto | throw exception
    //    - findByIdAndUserId(id, userId)
    // ----------------------------------------------------------
}
