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

import org.springframework.data.mongodb.core.query.Update;

@RestController
@RequestMapping("/api/devices")
@RequiredArgsConstructor
public class DeviceController {

    private final MongoTemplate mongoTemplate;

    @PostMapping
    public ResponseEntity<DeviceDto> create(
            @RequestBody DeviceDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        if (dto.macAddress == null || dto.macAddress.isBlank()) {
            dto.message = "MAC Address la bat buoc";
            return ResponseEntity.badRequest().body(dto);
        }

        String normalizedMac = normalizeMac(dto.macAddress);

        Query checkMac = new Query(Criteria.where("mac_address").is(normalizedMac));
        DeviceEntity existing = mongoTemplate.findOne(checkMac, DeviceEntity.class);
        if (existing != null) {
            dto.message = "MAC Address da ton tai";
            return ResponseEntity.status(HttpStatus.CONFLICT).body(dto);
        }

        Query checkDatalake = new Query(
                Criteria.where("mac_address").regex(normalizedMac, "i")
        ).limit(1);
        Document existingData = mongoTemplate.findOne(checkDatalake, Document.class, "datalake_raw");

        if (existingData == null) {
            dto.message = "MAC Address khong ton tai trong he thong";
            return ResponseEntity.status(HttpStatus.CONFLICT).body(dto);
        }

        DeviceEntity device = new DeviceEntity();
        device.userId = uid;
        device.macAddress = normalizedMac;
        device.name = dto.name;
        device.createdAt = Instant.now();

        DeviceEntity saved = mongoTemplate.save(device);

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
        return mac.trim().toUpperCase();
    }

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

    @PatchMapping("/{id}")
    public ResponseEntity<DeviceDto> rename(
            @PathVariable String id,
            @RequestBody DeviceDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        if (dto.name == null || dto.name.isBlank()) {
            DeviceDto err = new DeviceDto();
            err.message = "Ten thiet bi khong duoc de trong";
            return ResponseEntity.badRequest().body(err);
        }

        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(uid));

        DeviceEntity device = mongoTemplate.findOne(query, DeviceEntity.class);
        if (device == null) {
            return ResponseEntity.notFound().build();
        }

        Update update = new Update().set("name", dto.name.trim());
        mongoTemplate.updateFirst(query, update, DeviceEntity.class);

        device.name = dto.name.trim();
        DeviceDto response = toDto(device);
        response.message = "Doi ten thanh cong";
        return ResponseEntity.ok(response);
    }

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
