package com.iomt.dashboard.components.diary;

import java.time.Instant;

/**
 * DTO gộp: Request (tạo/sửa) + Response.
 *
 * Request (tạo/sửa):
 *   - title   : bắt buộc, không trống
 *   - content : bắt buộc, không trống
 *
 * Response:
 *   - id        : ObjectId (null khi tạo mới)
 *   - title     : tiêu đề
 *   - content   : nội dung
 *   - createdAt : thời điểm tạo (null khi request)
 */
public class DiaryDto {

    /** ID ghi chú — chỉ có trong response, null khi tạo mới */
    private String id;

    /** Tiêu đề ghi chú — bắt buộc khi tạo/sửa */
    private String title;

    /** Nội dung chi tiết — bắt buộc khi tạo/sửa */
    private String content;

    /** Thời điểm tạo — chỉ có trong response */
    private Instant createdAt;

    public DiaryDto() {}

    public DiaryDto(String id, String title, String content, Instant createdAt) {
        this.id = id;
        this.title = title;
        this.content = content;
        this.createdAt = createdAt;
    }

    // ── Getters ──────────────────────────────────────────
    public String getId() { return id; }
    public String getTitle() { return title; }
    public String getContent() { return content; }
    public Instant getCreatedAt() { return createdAt; }

    // ── Setters ──────────────────────────────────────────
    public void setId(String id) { this.id = id; }
    public void setTitle(String title) { this.title = title; }
    public void setContent(String content) { this.content = content; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    // ── Builder ──────────────────────────────────────────
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private String id;
        private String title;
        private String content;
        private Instant createdAt;

        public Builder id(String id) { this.id = id; return this; }
        public Builder title(String title) { this.title = title; return this; }
        public Builder content(String content) { this.content = content; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public DiaryDto build() { return new DiaryDto(id, title, content, createdAt); }
    }

    // ── Factory methods ──────────────────────────────────────────

    /** Chuyển Entity → DTO (response) */
    public static DiaryDto fromEntity(DiaryNote note) {
        return DiaryDto.builder()
                .id(note.getId())
                .title(note.getTitle())
                .content(note.getContent())
                .createdAt(note.getCreatedAt())
                .build();
    }

    /** Tạo Entity từ DTO (request) — chưa có id, createdAt */
    public DiaryNote toEntity(String userId) {
        return DiaryNote.builder()
                .userId(userId)
                .title(this.title)
                .content(this.content)
                .createdAt(Instant.now())
                .build();
    }
}
