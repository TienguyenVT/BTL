package com.iomt.dashboard.components.auth;

/**
 * ============================================================
 * AuthController — REST Controller: Xac thuc nguoi dung
 * ============================================================
 *
 * BASE PATH: /api/auth
 * SECURITY:  Public (khong can JWT)
 *
 * ENDPOINTS:
 *
 *    POST /api/auth/register
 *       INPUT : { email, password, name }
 *       OUTPUT: 201 + AuthDto | 409 Conflict
 *
 *    POST /api/auth/login
 *       INPUT : { email, password }
 *       OUTPUT: 200 + AuthDto (co token) | 401 Unauthorized
 *
 * RESPONSE (AuthDto):
 *    {
 *        "id": "65f...",
 *        "email": "user@example.com",
 *        "name": "Nguyen Van A",
 *        "token": "eyJhbGci..."   <- chi co khi login, null khi register
 *    }
 */
public class AuthController {

    // ----------------------------------------------------------
    // POST /api/auth/register
    //    @PostMapping("/register")
    //    public ResponseEntity<AuthDto> register(@RequestBody AuthDto dto) {
    //        AuthDto created = authService.register(dto);
    //        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    //    }
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // POST /api/auth/login
    //    @PostMapping("/login")
    //    public ResponseEntity<AuthDto> login(@RequestBody AuthDto dto) {
    //        AuthDto result = authService.login(dto);
    //        return ResponseEntity.ok(result);
    //    }
    // ----------------------------------------------------------
}
