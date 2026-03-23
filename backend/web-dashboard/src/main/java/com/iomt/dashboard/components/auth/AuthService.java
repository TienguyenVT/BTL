package com.iomt.dashboard.components.auth;

/**
 * ============================================================
 * AuthService — Service: Đăng ký & Đăng nhập
 * ============================================================
 *
 * NGHIEP VU:
 *    - register(request) : Tao tai khoan moi, ma hoa mat khau BCrypt
 *    - login(request)   : Kiem tra mat khau, tra ve JWT token
 *
 * LUONG XU LY:
 *    register:
 *      1. Kiem tra email da ton tai? -> 409 Conflict
 *      2. Ma hoa mat khau (BCrypt)
 *      3. Luu AuthEntity vao MongoDB
 *      4. Tra ve AuthEntity (khong tra ve password)
 *
 *    login:
 *      1. Tim AuthEntity theo email -> khong ton tai? -> 401
 *      2. Giai ma mat khau (BCrypt.matches) -> sai? -> 401
 *      3. Sinh JWT token (JwtTokenProvider)
 *      4. Tra ve AuthDto { id, email, name, token }
 */
public class AuthService {

    // ----------------------------------------------------------
    // register(AuthDto request)
    //    INPUT : email, password, name
    //    OUTPUT: AuthDto (khong co password)
    //    1. findByEmail -> da ton tai? -> throw EmailExistsException
    //    2. password = BCrypt.encode(password)
    //    3. save(new AuthEntity(...))
    //    4. return new AuthDto(entity.getId(), entity.getEmail(), entity.getName(), null)
    // ----------------------------------------------------------

    // ----------------------------------------------------------
    // login(AuthDto request)
    //    INPUT : email, password
    //    OUTPUT: AuthDto { id, email, name, token }
    //    1. findByEmail -> khong ton tai? -> throw UnauthorizedException
    //    2. BCrypt.matches(password, entity.password) -> sai? -> throw UnauthorizedException
    //    3. token = JwtTokenProvider.generateToken(entity.getId())
    //    4. return new AuthDto(entity.getId(), entity.getEmail(), entity.getName(), token)
    // ----------------------------------------------------------
}
