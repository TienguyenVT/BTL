package com.iomt.dashboard.components.profile;

import com.iomt.dashboard.common.UserUtils;
import lombok.RequiredArgsConstructor;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;

/**
 * Controller: Quan ly thong tin ca nhan (Profile).
 * Nguoi dung xem va cap nhat thong tin sinh truc hoc.
 *
 * Base path: /api/profile
 *
 * ENDPOINTS:
 *    GET /api/profile   — Xem profile + tinh BMI
 *    PUT /api/profile   — Cap nhat profile
 */
@RestController
@RequestMapping("/api/profile")
@RequiredArgsConstructor
public class ProfileController {

    private final MongoTemplate mongoTemplate;

    // ================================================================
    // GET /api/profile
    //    Lay profile cua user. Tao mac dinh neu chua co.
    //    Output: ProfileDto (co tinh BMI dong)
    // ================================================================
    @GetMapping
    public ResponseEntity<ProfileDto> get(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("user_id").is(uid));
        ProfileEntity profile = mongoTemplate.findOne(query, ProfileEntity.class);

        // Neu chua co, tao profile mac dinh
        if (profile == null) {
            profile = new ProfileEntity();
            profile.userId = uid;
            profile.age = null;
            profile.height = null;
            profile.weight = null;
            profile.updatedAt = null;
            mongoTemplate.save(profile);
        }

        return ResponseEntity.ok(toDto(profile));
    }

    // ================================================================
    // PUT /api/profile
    //    Cap nhat profile. Chi cap nhat cac truong khac null.
    //    Input: { age, height, weight }
    //    Output: ProfileDto (da cap nhat)
    // ================================================================
    @PutMapping
    public ResponseEntity<ProfileDto> update(
            @RequestBody ProfileDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("user_id").is(uid));
        ProfileEntity profile = mongoTemplate.findOne(query, ProfileEntity.class);

        // Neu chua co, tao moi
        if (profile == null) {
            profile = new ProfileEntity();
            profile.userId = uid;
        }

        // Cap nhat cac truong khac null
        if (dto.age != null) {
            profile.age = dto.age;
        }
        if (dto.height != null) {
            profile.height = dto.height;
        }
        if (dto.weight != null) {
            profile.weight = dto.weight;
        }

        profile.updatedAt = Instant.now();
        mongoTemplate.save(profile);

        return ResponseEntity.ok(toDto(profile));
    }

    // ================================================================
    // Chuyen Entity -> DTO, tinh BMI dong
    // ================================================================
    private ProfileDto toDto(ProfileEntity entity) {
        ProfileDto dto = new ProfileDto();
        dto.userId = entity.userId;
        dto.age = entity.age;
        dto.height = entity.height;
        dto.weight = entity.weight;
        dto.updatedAt = entity.updatedAt;

        // Tinh BMI dong: weight / (height/100)^2
        if (entity.height != null && entity.weight != null
                && entity.height > 0) {
            double heightM = entity.height / 100.0;
            dto.bmi = Math.round((entity.weight / (heightM * heightM)) * 10.0) / 10.0;
        } else {
            dto.bmi = null;
        }

        return dto;
    }
}
