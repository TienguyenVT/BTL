package com.iomt.dashboard.components.auth;

import lombok.RequiredArgsConstructor;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final MongoTemplate mongoTemplate;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    @PostMapping("/register")
    public ResponseEntity<AuthDto> register(@RequestBody AuthDto dto) {

        if (dto.email == null || dto.email.isBlank()
                || dto.password == null || dto.password.isBlank()
                || dto.name == null || dto.name.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("Email, password, name la bat buoc");
            return ResponseEntity.badRequest().body(error);
        }

        Query checkEmail = new Query(Criteria.where("email").is(dto.email));
        AuthEntity existing = mongoTemplate.findOne(checkEmail, AuthEntity.class);
        if (existing != null) {
            AuthDto error = new AuthDto();
            error.setMessage("Email da ton tai");
            return ResponseEntity.status(HttpStatus.CONFLICT).body(error);
        }

        AuthEntity newUser = new AuthEntity();
        newUser.email = dto.email;
        newUser.password = encoder.encode(dto.password);
        newUser.name = dto.name;
        newUser.createdAt = Instant.now();

        AuthEntity saved = mongoTemplate.save(newUser);

        AuthDto response = new AuthDto();
        response.id = saved.id;
        response.name = saved.name;
        response.message = "Dang ky thanh cong";
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/me")
    public ResponseEntity<AuthDto> me(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        if (userId == null || userId.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("X-User-Id header required");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        Query query = new Query(Criteria.where("_id").is(userId));
        AuthEntity user = mongoTemplate.findOne(query, AuthEntity.class);
        if (user == null) {
            AuthDto error = new AuthDto();
            error.setMessage("Tai khoan khong ton tai");
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
        }

        AuthDto response = new AuthDto();
        response.id = user.id;
        response.email = user.email;
        response.name = user.name;
        return ResponseEntity.ok(response);
    }

    @PostMapping("/login")
    public ResponseEntity<AuthDto> login(@RequestBody AuthDto dto) {

        if (dto.email == null || dto.email.isBlank()
                || dto.password == null || dto.password.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("Email va password la bat buoc");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        Query findByEmail = new Query(Criteria.where("email").is(dto.email));
        AuthEntity user = mongoTemplate.findOne(findByEmail, AuthEntity.class);
        if (user == null) {
            AuthDto error = new AuthDto();
            error.setMessage("Email khong ton tai");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        if (!encoder.matches(dto.password, user.password)) {
            AuthDto error = new AuthDto();
            error.setMessage("Mat khau khong dung");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        AuthDto response = new AuthDto();
        response.id = user.id;
        response.name = user.name;
        response.message = "Dang nhap thanh cong";
        return ResponseEntity.ok(response);
    }

    @PutMapping
    public ResponseEntity<AuthDto> update(
            @RequestBody AuthDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        System.out.println("[DEBUG] PUT /api/auth called - userId: " + userId + ", name: " + dto.name);

        if (userId == null || userId.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("X-User-Id header required");
            System.out.println("[DEBUG] Missing X-User-Id header");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        Query query = new Query(Criteria.where("_id").is(userId));
        AuthEntity user = mongoTemplate.findOne(query, AuthEntity.class);
        System.out.println("[DEBUG] user from DB: " + (user != null ? user.name : "NULL"));
        if (user == null) {
            AuthDto error = new AuthDto();
            error.setMessage("Tai khoan khong ton tai");
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
        }

        if (dto.password == null || dto.password.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("Mat khau hien tai la bat buoc de xac nhan");
            return ResponseEntity.badRequest().body(error);
        }

        if (!encoder.matches(dto.password, user.password)) {
            AuthDto error = new AuthDto();
            error.setMessage("Mat khau hien tai khong dung");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        if (dto.name != null && !dto.name.isBlank()) {
            user.name = dto.name;
        } else {
            AuthDto error = new AuthDto();
            error.setMessage("Ten la bat buoc");
            return ResponseEntity.badRequest().body(error);
        }

        mongoTemplate.save(user);
        System.out.println("[DEBUG] save done, new name: " + user.name);

        AuthDto response = new AuthDto();
        response.id = user.id;
        response.name = user.name;
        response.message = "Cap nhat thanh cong";
        return ResponseEntity.ok(response);
    }

    @DeleteMapping
    public ResponseEntity<AuthDto> delete(
            @RequestBody AuthDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        if (userId == null || userId.isBlank()) {
            AuthDto error = new AuthDto();
            error.setMessage("X-User-Id header required");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        Query query = new Query(Criteria.where("_id").is(userId));
        AuthEntity user = mongoTemplate.findOne(query, AuthEntity.class);
        if (user == null) {
            AuthDto error = new AuthDto();
            error.setMessage("Tai khoan khong ton tai");
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
        }

        if (dto.password == null || dto.password.isBlank()
                || !encoder.matches(dto.password, user.password)) {
            AuthDto error = new AuthDto();
            error.setMessage("Mat khau khong dung");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }

        mongoTemplate.remove(query, AuthEntity.class);

        AuthDto response = new AuthDto();
        response.message = "Tai khoan da duoc xoa";
        return ResponseEntity.ok(response);
    }
}
