package com.iomt.dashboard.components.diary;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * Entity: Sổ tay sức khỏe cá nhân.
 * Collection: "diary_notes"
 *
 * Các trường mới:
 *   - noteTimestamp : Mốc thời gian ghi chú đề cập (để đối chiếu biểu đồ)
 *   - alertId       : ID alert đã trigger ghi chú (nullable)
 *   - activity      : Hoạt động tại thời điểm đó
 *   - mood          : Tâm trạng
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

    /** Mốc thời gian mà ghi chú đề cập (để đối chiếu biểu đồ BPM/GSR) */
    @Field("note_timestamp")
    private Instant noteTimestamp;

    /** ID alert đã trigger ghi chú (nullable) */
    @Field("alert_id")
    private String alertId;

    /** Hoạt động tại thời điểm đó (ví dụ: "đang thuyết trình", "tập gym") */
    @Field("activity")
    private String activity;

    /** Tâm trạng (ví dụ: "lo lắng", "bình thường", "mệt mỏi") */
    @Field("mood")
    private String mood;

    public DiaryNote() {}

    public DiaryNote(String id, String userId, String title, String content, Instant createdAt,
                     Instant noteTimestamp, String alertId, String activity, String mood) {
        this.id = id;
        this.userId = userId;
        this.title = title;
        this.content = content;
        this.createdAt = createdAt;
        this.noteTimestamp = noteTimestamp;
        this.alertId = alertId;
        this.activity = activity;
        this.mood = mood;
    }

    // ── Getters ──────────────────────────────────────────
    public String getId() { return id; }
    public String getUserId() { return userId; }
    public String getTitle() { return title; }
    public String getContent() { return content; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getNoteTimestamp() { return noteTimestamp; }
    public String getAlertId() { return alertId; }
    public String getActivity() { return activity; }
    public String getMood() { return mood; }

    // ── Setters ──────────────────────────────────────────
    public void setId(String id) { this.id = id; }
    public void setUserId(String userId) { this.userId = userId; }
    public void setTitle(String title) { this.title = title; }
    public void setContent(String content) { this.content = content; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public void setNoteTimestamp(Instant noteTimestamp) { this.noteTimestamp = noteTimestamp; }
    public void setAlertId(String alertId) { this.alertId = alertId; }
    public void setActivity(String activity) { this.activity = activity; }
    public void setMood(String mood) { this.mood = mood; }

    // ── Builder ──────────────────────────────────────────
    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private String id;
        private String userId;
        private String title;
        private String content;
        private Instant createdAt;
        private Instant noteTimestamp;
        private String alertId;
        private String activity;
        private String mood;

        public Builder id(String id) { this.id = id; return this; }
        public Builder userId(String userId) { this.userId = userId; return this; }
        public Builder title(String title) { this.title = title; return this; }
        public Builder content(String content) { this.content = content; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public Builder noteTimestamp(Instant noteTimestamp) { this.noteTimestamp = noteTimestamp; return this; }
        public Builder alertId(String alertId) { this.alertId = alertId; return this; }
        public Builder activity(String activity) { this.activity = activity; return this; }
        public Builder mood(String mood) { this.mood = mood; return this; }
        public DiaryNote build() {
            return new DiaryNote(id, userId, title, content, createdAt, noteTimestamp, alertId, activity, mood);
        }
    }
}
