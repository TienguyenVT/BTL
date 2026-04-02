package com.iomt.dashboard.components.auth;

import lombok.RequiredArgsConstructor;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;

/**
 * Controller: Xac thuc nguoi dung (dang ky / dang nhap).
 *
 * Base path: /api/auth
 * Auth:      Public (khong can JWT)
 *
 * ENDPOINTS:
 *    POST /api/auth/register   — Tao tai khoan moi
 *    POST /api/auth/login       — Dang nhap
 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final MongoTemplate mongoTemplate;

    // ================================================================
    // POST /api/auth/register
    //    Tao tai khoan moi.
    //    Input: { email, password, name }
    //    Output: 201 + { id, name, message } | 400 | 409
    // ================================================================
    @PostMapping("/register")
    public ResponseEntity<AuthDto> register(@RequestBody AuthDto dto) {

        // 1. Kiem tra dau vao
        if (dto.email == null || dto.email.isBlank()
                || dto.password == null || dto.password.isBlank()
                || dto.name == null || dto.name.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("Email, password, name la bat buoc");
            return ResponseEntity.badRequest().body(error);
        }

        // 2. Kiem tra email da ton tai chua
        Query checkEmail = new Query(Criteria.where("email").is(dto.email));
        AuthEntity existing = mongoTemplate.findOne(checkEmail, AuthEntity.class);
        if (existing != null) {
            AuthDto error = new AuthDto();
            error.setMessage("Email da ton tai");
            return ResponseEntity.status(HttpStatus.CONFLICT).body(error);
        }

        // 3. Tao tai khoan moi
        AuthEntity newUser = new AuthEntity();
        newUser.email = dto.email;
        newUser.password = dto.password; // plain text (chi de demo)
        newUser.name = dto.name;
        newUser.createdAt = Instant.now();

        AuthEntity saved = mongoTemplate.save(newUser);

        // 4. Tra ve ket qua
        AuthDto response = new AuthDto();
        response.id = saved.id;
        response.name = saved.name;
        response.message = "Dang ky thanh cong";
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    // ================================================================
    // POST /api/auth/login
    //    Dang nhap.
    //    Input: { email, password }
    //    Output: 200 + { id, name, message } | 401
    // ================================================================
    @PostMapping("/login")
    public ResponseEntity<AuthDto> login(@RequestBody AuthDto dto) {

        // 1. Kiem tra dau vao
        if (dto.email == null || dto.email.isBlank()
                || dto.password == null || dto.password.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("Email va password la bat buoc");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        // 2. Tim tai khoan theo email
        Query findByEmail = new Query(Criteria.where("email").is(dto.email));
        AuthEntity user = mongoTemplate.findOne(findByEmail, AuthEntity.class);
        if (user == null) {
            AuthDto error = new AuthDto();
            error.setMessage("Email khong ton tai");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        // 3. Kiem tra mat khau
        if (!user.password.equals(dto.password)) {
            AuthDto error = new AuthDto();
            error.setMessage("Mat khau khong dung");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        // 4. Dang nhap thanh cong
        AuthDto response = new AuthDto();
        response.id = user.id;
        response.name = user.name;
        response.message = "Dang nhap thanh cong";
        return ResponseEntity.ok(response);
    }
}
