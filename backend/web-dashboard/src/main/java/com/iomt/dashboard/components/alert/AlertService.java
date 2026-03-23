package com.iomt.dashboard.components.alert;

/**
 * ============================================================
 * AlertService — Service: Quan ly canh bao
 * ============================================================
 *
 * NGHIEP VU:
 *    - getAll(userId)        : Lay danh sach canh bao
 *    - getUnreadCount(userId) : Dem so canh bao chua doc
 *    - delete(id, userId)    : Xoa canh bao
 *
 * getAll(userId):
 *    1. Tim tat ca theo userId (sort timestamp desc)
 *    2. Tra ve List<AlertDto>
 *
 * getUnreadCount(userId):
 *    1. Dem so Alert co isRead = false
 *    2. Tra ve long
 *
 * delete(id, userId):
 *    1. Tim theo id + userId -> khong tim thay? -> 404
 *    2. Xoa khoi MongoDB
 *
 * LY DO KHONG CO TAO:
 *    Alert duoc tao tu dong boi AI/he thong khi label = Stress/Fever.
 *    User chi xem va xoa, khong tu tao.
 */
public class AlertService {

    // ----------------------------------------------------------
    // getAll(String userId)
    //    INPUT : userId
    //    OUTPUT: List<AlertDto>
    //    - alertRepository.findByUserIdOrderByTimestampDesc(userId)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // getUnreadCount(String userId)
    //    INPUT : userId
    //    OUTPUT: long
    //    - alertRepository.countByUserIdAndIsReadFalse(userId)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // delete(String id, String userId)
    //    INPUT : id, userId
    //    OUTPUT: void | throw exception
    //    - alertRepository.findByIdAndUserId(id, userId)
    //    - alertRepository.delete(alert)
    // ----------------------------------------------------------
}
