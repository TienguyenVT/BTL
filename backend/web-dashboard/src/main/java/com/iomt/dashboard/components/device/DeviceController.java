package com.iomt.dashboard.components.device;

import com.iomt.dashboard.common.UserUtils;
import lombok.RequiredArgsConstructor;
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

        // 2. Kiem tra MAC da ton tai chua
        Query checkMac = new Query(Criteria.where("mac_address").is(dto.macAddress));
        DeviceEntity existing = mongoTemplate.findOne(checkMac, DeviceEntity.class);
        if (existing != null) {
            dto.message = "MAC Address da ton tai";
            return ResponseEntity.status(HttpStatus.CONFLICT).body(dto);
        }

        // 3. Tao thiet bi moi
        DeviceEntity device = new DeviceEntity();
        device.userId = uid;
        device.macAddress = dto.macAddress;
        device.name = dto.name;
        device.createdAt = Instant.now();

        DeviceEntity saved = mongoTemplate.save(device);

        // 4. Tra ve ket qua
        DeviceDto response = new DeviceDto();
        response.id = saved.id;
        response.macAddress = saved.macAddress;
        response.name = saved.name;
        response.createdAt = saved.createdAt;
        response.message = "Them thiet bi thanh cong";
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
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
