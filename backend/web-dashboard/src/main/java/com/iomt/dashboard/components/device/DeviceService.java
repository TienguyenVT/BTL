package com.iomt.dashboard.components.device;

/**
 * ============================================================
 * DeviceService — Service: Quan ly thiet bi ESP32
 * ============================================================
 *
 * NGHIEP VU:
 *    - create(userId, dto)  : Them thiet bi moi
 *    - getAll(userId)       : Lay danh sach thiet bi
 *    - delete(id, userId)   : Xoa thiet bi
 *
 * create(userId, dto):
 *    1. Kiem tra macAddress da ton tai? -> 409 Conflict
 *    2. Tao DeviceEntity, set userId, macAddress, name, createdAt
 *    3. save()
 *    4. Tra ve DeviceDto
 *
 * getAll(userId):
 *    1. Tim tat ca theo userId (sort createdAt desc)
 *    2. Tra ve List<DeviceDto>
 *
 * delete(id, userId):
 *    1. Tim theo id + userId -> khong tim thay? -> 404
 *    2. Xoa khoi MongoDB
 */
public class DeviceService {

    // ----------------------------------------------------------
    // create(String userId, DeviceDto dto)
    //    INPUT : userId, dto { macAddress, name }
    //    OUTPUT: DeviceDto | 409 (MAC da ton tai)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // getAll(String userId)
    //    INPUT : userId
    //    OUTPUT: List<DeviceDto>
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // delete(String id, String userId)
    //    INPUT : id, userId
    //    OUTPUT: void | 404 (khong tim thay)
    // ----------------------------------------------------------
}
