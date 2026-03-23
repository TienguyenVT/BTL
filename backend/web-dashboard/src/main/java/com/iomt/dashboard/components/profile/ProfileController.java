package com.iomt.dashboard.components.profile;

/**
 * ============================================================
 * ProfileController — REST Controller: Quan ly thong tin ca nhan
 * ============================================================
 *
 * BASE PATH: /api/profile
 * SECURITY:  Protected (can JWT)
 *
 * ENDPOINTS:
 *
 *    GET /api/profile
 *       Lay profile cua user hien tai.
 *       OUTPUT: 200 + ProfileDto | 401
 *
 *    PUT /api/profile
 *       Cap nhat profile cua user hien tai.
 *       INPUT : { age, height, weight } (optional)
 *       OUTPUT: 200 + ProfileDto | 401
 *
 * RESPONSE (ProfileDto):
 *    {
 *        "userId": "65f...",
 *        "age": 25,
 *        "height": 170.5,
 *        "weight": 65.0,
 *        "bmi": 22.4
 *    }
 */
public class ProfileController {

    // ----------------------------------------------------------
    // GET /api/profile
    //    @GetMapping
    //    public ResponseEntity<ProfileDto> get() {
    //        String userId = getCurrentUserId();
    //        return ResponseEntity.ok(profileService.get(userId));
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // PUT /api/profile
    //    @PutMapping
    //    public ResponseEntity<ProfileDto> update(@RequestBody ProfileDto dto) {
    //        String userId = getCurrentUserId();
    //        return ResponseEntity.ok(profileService.update(userId, dto));
    //    }
    // ----------------------------------------------------------
}
