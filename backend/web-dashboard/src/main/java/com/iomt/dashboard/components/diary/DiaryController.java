package com.iomt.dashboard.components.diary;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

/**
 * Controller + Service gộp: Sổ tay sức khỏe cá nhân.
 *
 * Base path: /api/diary-notes
 * Auth:      Public (tạm thời — sẽ thêm JWT sau)
 *
 * CRUD đầy đủ:
 *   POST   /diary-notes           — Tạo ghi chú
 *   GET    /diary-notes           — Danh sách (mới nhất trước)
 *   GET    /diary-notes/{id}      — Chi tiết 1 ghi chú
 *   PUT    /diary-notes/{id}      — Sửa ghi chú
 *   DELETE /diary-notes/{id}      — Xóa ghi chú
 */
@RestController
@RequestMapping("/api/diary-notes")
@RequiredArgsConstructor
public class DiaryController {

    private final MongoTemplate mongoTemplate;

    // ================================================================
    // SERVICE LAYER (embedded)
    // ================================================================

    /** Tạo ghi chú mới */
    private DiaryDto create(String userId, DiaryDto dto) {
        DiaryNote note = dto.toEntity(userId);
        DiaryNote saved = mongoTemplate.save(note);
        return DiaryDto.fromEntity(saved);
    }

    /** Lấy tất cả ghi chú của user (mới nhất trước) */
    private List<DiaryDto> getAll(String userId) {
        Query query = new Query(Criteria.where("user_id").is(userId))
                .with(Sort.by(Sort.Direction.DESC, "created_at"));
        return mongoTemplate.find(query, DiaryNote.class)
                .stream()
                .map(DiaryDto::fromEntity)
                .toList();
    }

    /** Lấy 1 ghi chú theo id + userId */
    private Optional<DiaryNote> findByIdAndUserId(String id, String userId) {
        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(userId));
        return Optional.ofNullable(mongoTemplate.findOne(query, DiaryNote.class));
    }

    // ================================================================
    // REST ENDPOINTS
    // ================================================================

    /**
     * POST /api/diary-notes
     * Tạo ghi chú mới.
     */
    @PostMapping
    public ResponseEntity<DiaryDto> create(
            @Valid @RequestBody DiaryDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        // Fallback: nếu không có header, dùng user cố định (demo)
        String uid = (userId != null && !userId.isBlank()) ? userId : "demo_user";

        DiaryDto created = create(uid, dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    /**
     * GET /api/diary-notes
     * Lấy danh sách ghi chú.
     */
    @GetMapping
    public ResponseEntity<List<DiaryDto>> getAll(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = (userId != null && !userId.isBlank()) ? userId : "demo_user";
        return ResponseEntity.ok(getAll(uid));
    }

    /**
     * GET /api/diary-notes/{id}
     * Lấy chi tiết 1 ghi chú.
     */
    @GetMapping("/{id}")
    public ResponseEntity<DiaryDto> getById(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = (userId != null && !userId.isBlank()) ? userId : "demo_user";
        return findByIdAndUserId(id, uid)
                .map(note -> ResponseEntity.ok(DiaryDto.fromEntity(note)))
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * PUT /api/diary-notes/{id}
     * Sửa ghi chú (chỉ cập nhật trường khác null).
     */
    @PutMapping("/{id}")
    public ResponseEntity<DiaryDto> update(
            @PathVariable String id,
            @RequestBody DiaryDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = (userId != null && !userId.isBlank()) ? userId : "demo_user";

        return findByIdAndUserId(id, uid)
                .map(note -> {
                    if (dto.getTitle() != null) {
                        note.setTitle(dto.getTitle());
                    }
                    if (dto.getContent() != null) {
                        note.setContent(dto.getContent());
                    }
                    DiaryNote saved = mongoTemplate.save(note);
                    return ResponseEntity.ok(DiaryDto.fromEntity(saved));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * DELETE /api/diary-notes/{id}
     * Xóa ghi chú.
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = (userId != null && !userId.isBlank()) ? userId : "demo_user";

        return findByIdAndUserId(id, uid)
                .map(note -> {
                    mongoTemplate.remove(note);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
