package com.iomt.dashboard.components.device;

import com.iomt.dashboard.common.UserUtils;
import lombok.RequiredArgsConstructor;
import org.bson.Document;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Controller: Quan ly thiet bi ESP32.
 * Nguoi dung dang ky thiet bi bang MAC Address.
 *
 * Base path: /api/devices
 *
 * ENDPOINTS:
 *    POST /api/devices          — Them thiet bi
 *    GET /api/devices           — Danh sach thiet bi
 *    DELETE /api/devices/{id}   — Xoa thiet bi
 */
@RestController
@RequestMapping("/api/devices")
@RequiredArgsConstructor
public class DeviceController {

    private final MongoTemplate mongoTemplate;

    // ================================================================
    // POST /api/devices
    //    Them thiet bi moi.
    //    Input: { macAddress, name }
    //    Output: 201 + DeviceDto | 400 | 409
    // ================================================================
    @PostMapping
    public ResponseEntity<DeviceDto> create(
            @RequestBody DeviceDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        // 1. Kiem tra macAddress bat buoc
        if (dto.macAddress == null || dto.macAddress.isBlank()) {
            dto.message = "MAC Address la bat buoc";
            return ResponseEntity.badRequest().body(dto);
        }

        // 2. Normalize MAC address
        String normalizedMac = normalizeMac(dto.macAddress);

        // 3. Kiem tra MAC da ton tai chua
        Query checkMac = new Query(Criteria.where("mac_address").is(normalizedMac));
        DeviceEntity existing = mongoTemplate.findOne(checkMac, DeviceEntity.class);
        if (existing != null) {
            dto.message = "MAC Address da ton tai";
            return ResponseEntity.status(HttpStatus.CONFLICT).body(dto);
        }

        // 4. Kiem tra MAC co trong datalake_raw khong (verify device has data)
        Query checkDatalake = new Query(
                Criteria.where("mac_address").regex(normalizedMac, "i")
        ).limit(1);
        Document existingData = mongoTemplate.findOne(checkDatalake, Document.class, "datalake_raw");

        if (existingData == null) {
            dto.message = "MAC Address khong ton tai trong he thong";
            return ResponseEntity.status(HttpStatus.CONFLICT).body(dto);
        }

        // 5. Tao thiet bi moi
        DeviceEntity device = new DeviceEntity();
        device.userId = uid;
        device.macAddress = normalizedMac;
        device.name = dto.name;
        device.createdAt = Instant.now();

        DeviceEntity saved = mongoTemplate.save(device);

        // 6. Tra ve ket qua
        DeviceDto response = new DeviceDto();
        response.id = saved.id;
        response.macAddress = saved.macAddress;
        response.name = saved.name;
        response.createdAt = saved.createdAt;
        response.message = "Them thiet bi thanh cong";
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    private String normalizeMac(String mac) {
        if (mac == null) return null;
        return mac.trim().toLowerCase();
    }

    // ================================================================
    // GET /api/devices
    //    Lay danh sach thiet bi.
    //    Output: List<DeviceDto>
    // ================================================================
    @GetMapping
    public ResponseEntity<List<DeviceDto>> getAll(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("user_id").is(uid));
        query.with(org.springframework.data.domain.Sort.by(
                org.springframework.data.domain.Sort.Direction.DESC, "created_at"
        ));

        List<DeviceDto> devices = mongoTemplate.find(query, DeviceEntity.class)
                .stream()
                .map(this::toDto)
                .collect(Collectors.toList());

        return ResponseEntity.ok(devices);
    }

    // ================================================================
    // GET /api/devices/{id}
    //    Lay chi tiet thiet bi.
    //    Output: DeviceDto | 404
    // ================================================================
    @GetMapping("/{id}")
    public ResponseEntity<DeviceDto> getById(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(uid));

        DeviceEntity device = mongoTemplate.findOne(query, DeviceEntity.class);
        if (device == null) {
            return ResponseEntity.notFound().build();
        }

        return ResponseEntity.ok(toDto(device));
    }

    // ================================================================
    // DELETE /api/devices/{id}
    //    Xoa thiet bi.
    //    Output: 204 | 404
    // ================================================================
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(uid));

        DeviceEntity device = mongoTemplate.findOne(query, DeviceEntity.class);
        if (device == null) {
            return ResponseEntity.notFound().build();
        }

        mongoTemplate.remove(device);
        return ResponseEntity.noContent().build();
    }

    // ================================================================
    // Chuyen Entity -> DTO
    // ================================================================
    private DeviceDto toDto(DeviceEntity entity) {
        return new DeviceDto(
                entity.id,
                entity.macAddress,
                entity.name,
                entity.createdAt,
                null
        );
    }
}
