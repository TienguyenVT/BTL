package com.iomt.dashboard.components.diary;

import com.iomt.dashboard.common.UserUtils;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/diary-notes")
@RequiredArgsConstructor
public class DiaryController {

    private final MongoTemplate mongoTemplate;

    private DiaryDto create(String userId, DiaryDto dto) {
        DiaryNote note = dto.toEntity(userId);
        DiaryNote saved = mongoTemplate.save(note);
        return DiaryDto.fromEntity(saved);
    }

    private List<DiaryDto> findAllByUserId(String userId) {
        Query query = new Query(Criteria.where("user_id").is(userId))
                .with(Sort.by(Sort.Direction.DESC, "created_at"));
        return mongoTemplate.find(query, DiaryNote.class)
                .stream()
                .map(DiaryDto::fromEntity)
                .toList();
    }

    private Optional<DiaryNote> findByIdAndUserId(String id, String userId) {
        Query query = new Query(Criteria.where("_id").is(id)
                .and("user_id").is(userId));
        return Optional.ofNullable(mongoTemplate.findOne(query, DiaryNote.class));
    }

    @PostMapping
    public ResponseEntity<DiaryDto> create(
            @Valid @RequestBody DiaryDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        DiaryDto created = create(uid, dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping
    public ResponseEntity<List<DiaryDto>> getAll(
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        return ResponseEntity.ok(findAllByUserId(uid));
    }

    @GetMapping("/{id}")
    public ResponseEntity<DiaryDto> getById(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);
        return findByIdAndUserId(id, uid)
                .map(note -> ResponseEntity.ok(DiaryDto.fromEntity(note)))
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/by-time-range")
    public ResponseEntity<List<DiaryDto>> getByTimeRange(
            @RequestParam long from,
            @RequestParam long to,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        Instant fromInstant = Instant.ofEpochMilli(from);
        Instant toInstant = Instant.ofEpochMilli(to);

        Query query = new Query(
                Criteria.where("user_id").is(uid)
                        .and("note_timestamp").gte(fromInstant).lte(toInstant)
        ).with(Sort.by(Sort.Direction.ASC, "note_timestamp"));

        List<DiaryDto> notes = mongoTemplate.find(query, DiaryNote.class)
                .stream()
                .map(DiaryDto::fromEntity)
                .toList();

        return ResponseEntity.ok(notes);
    }

    @PutMapping("/{id}")
    public ResponseEntity<DiaryDto> update(
            @PathVariable String id,
            @RequestBody DiaryDto dto,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        return findByIdAndUserId(id, uid)
                .map(note -> {
                    if (dto.getTitle() != null) {
                        note.setTitle(dto.getTitle());
                    }
                    if (dto.getContent() != null) {
                        note.setContent(dto.getContent());
                    }
                    if (dto.getNoteTimestamp() != null) {
                        note.setNoteTimestamp(dto.getNoteTimestamp());
                    }
                    if (dto.getAlertId() != null) {
                        note.setAlertId(dto.getAlertId());
                    }
                    if (dto.getActivity() != null) {
                        note.setActivity(dto.getActivity());
                    }
                    if (dto.getMood() != null) {
                        note.setMood(dto.getMood());
                    }
                    DiaryNote saved = mongoTemplate.save(note);
                    return ResponseEntity.ok(DiaryDto.fromEntity(saved));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        String uid = UserUtils.extractUserId(userId);

        return findByIdAndUserId(id, uid)
                .map(note -> {
                    mongoTemplate.remove(note);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
