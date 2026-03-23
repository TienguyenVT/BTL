package com.iomt.dashboard.components.profile;

/**
 * ============================================================
 * ProfileService — Service: Xem & Cap nhat thong tin ca nhan
 * ============================================================
 *
 * NGHIEP VU:
 *    - get(userId)    : Lay profile cua user (tao mac dinh neu chua co)
 *    - update(userId) : Cap nhat profile (chi cap nhat cac truong khac null)
 *
 * get(userId):
 *    1. Tim theo userId -> chua co? -> tao ProfileEntity mac dinh (null fields)
 *    2. Tinh BMI dong (weight / (height/100)^2)
 *    3. Tra ve ProfileDto
 *
 * update(userId, dto):
 *    1. Tim theo userId -> chua co? -> tao moi
 *    2. Cap nhat cac truong khac null
 *    3. Set updatedAt = now()
 *    4. save()
 *    5. Tra ve ProfileDto
 */
public class ProfileService {

    // ----------------------------------------------------------
    // get(String userId)
    //    INPUT : userId
    //    OUTPUT: ProfileDto (co tinh BMI dong)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // update(String userId, ProfileDto dto)
    //    INPUT : userId, dto (cac truong optional)
    //    OUTPUT: ProfileDto (da cap nhat)
    // ----------------------------------------------------------
}
