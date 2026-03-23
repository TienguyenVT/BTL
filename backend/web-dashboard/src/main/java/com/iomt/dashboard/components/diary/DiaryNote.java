package com.iomt.dashboard.components.diary;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * Entity: Sổ tay sức khỏe cá nhân.
 * Collection: "diary_notes"
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
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
}
