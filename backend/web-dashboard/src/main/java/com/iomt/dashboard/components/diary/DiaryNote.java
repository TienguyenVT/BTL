package com.iomt.dashboard.components.diary;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * Entity: Sổ tay sức khỏe cá nhân.
 * Collection: "diary_notes"
 */
@Document(collection = "diary_notes")
public class DiaryNote {

    @Id
    private String id;

    /** ID người dùng sở hữu ghi chú */
    @Indexed
    @Field("user_id")
    private String userId;

    /** Tiêu đề ghi chú */
    @Field("title")
    private String title;

    /** Nội dung chi tiết */
    @Field("content")
    private String content;

    /** Thời điểm tạo */
    @Field("created_at")
    private Instant createdAt;

    public DiaryNote() {}

    public DiaryNote(String id, String userId, String title, String content, Instant createdAt) {
        this.id = id;
        this.userId = userId;
        this.title = title;
        this.content = content;
        this.createdAt = createdAt;
    }

    // ── Getters ──────────────────────────────────────────
    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getTitle() { return title; }
    public String getContent() { return content; }
    public Instant getCreatedAt() { return createdAt; }

    // ── Setters ──────────────────────────────────────────
    public void setId(String id) { this.id = id; }
    public void setUserId(String userId) { this.userId = userId; }
    public void setTitle(String title) { this.title = title; }
    public void setContent(String content) { this.content = content; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    // ── Builder ──────────────────────────────────────────
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private String id;
        private String userId;
        private String title;
        private String content;
        private Instant createdAt;

        public Builder id(String id) { this.id = id; return this; }
        public Builder userId(String userId) { this.userId = userId; return this; }
        public Builder title(String title) { this.title = title; return this; }
        public Builder content(String content) { this.content = content; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public DiaryNote build() { return new DiaryNote(id, userId, title, content, createdAt); }
    }
}
