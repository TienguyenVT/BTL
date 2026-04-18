package com.iomt.dashboard.components.diary;

import java.time.Instant;

public class DiaryDto {

    private String id;
    private String title;
    private String content;
    private Instant createdAt;
    private Instant noteTimestamp;
    private String alertId;
    private String activity;
    private String mood;

    public DiaryDto() {}

    public DiaryDto(String id, String title, String content, Instant createdAt,
                    Instant noteTimestamp, String alertId, String activity, String mood) {
        this.id = id;
        this.title = title;
        this.content = content;
        this.createdAt = createdAt;
        this.noteTimestamp = noteTimestamp;
        this.alertId = alertId;
        this.activity = activity;
        this.mood = mood;
    }

    public String getId() { return id; }
    public String getTitle() { return title; }
    public String getContent() { return content; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getNoteTimestamp() { return noteTimestamp; }
    public String getAlertId() { return alertId; }
    public String getActivity() { return activity; }
    public String getMood() { return mood; }

    public void setId(String id) { this.id = id; }
    public void setTitle(String title) { this.title = title; }
    public void setContent(String content) { this.content = content; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public void setNoteTimestamp(Instant noteTimestamp) { this.noteTimestamp = noteTimestamp; }
    public void setAlertId(String alertId) { this.alertId = alertId; }
    public void setActivity(String activity) { this.activity = activity; }
    public void setMood(String mood) { this.mood = mood; }

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private String id;
        private String title;
        private String content;
        private Instant createdAt;
        private Instant noteTimestamp;
        private String alertId;
        private String activity;
        private String mood;

        public Builder id(String id) { this.id = id; return this; }
        public Builder title(String title) { this.title = title; return this; }
        public Builder content(String content) { this.content = content; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public Builder noteTimestamp(Instant noteTimestamp) { this.noteTimestamp = noteTimestamp; return this; }
        public Builder alertId(String alertId) { this.alertId = alertId; return this; }
        public Builder activity(String activity) { this.activity = activity; return this; }
        public Builder mood(String mood) { this.mood = mood; return this; }
        public DiaryDto build() {
            return new DiaryDto(id, title, content, createdAt, noteTimestamp, alertId, activity, mood);
        }
    }

    public static DiaryDto fromEntity(DiaryNote note) {
        return DiaryDto.builder()
                .id(note.getId())
                .title(note.getTitle())
                .content(note.getContent())
                .createdAt(note.getCreatedAt())
                .noteTimestamp(note.getNoteTimestamp())
                .alertId(note.getAlertId())
                .activity(note.getActivity())
                .mood(note.getMood())
                .build();
    }

    public DiaryNote toEntity(String userId) {
        return DiaryNote.builder()
                .userId(userId)
                .title(this.title)
                .content(this.content)
                .createdAt(Instant.now())
                .noteTimestamp(this.noteTimestamp)
                .alertId(this.alertId)
                .activity(this.activity)
                .mood(this.mood)
                .build();
    }
}
