package com.iomt.dashboard.components.diary;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

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
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DiaryDto {

    /** ID ghi chú — chỉ có trong response, null khi tạo mới */
    private String id;

    /** Tiêu đề ghi chú — bắt buộc khi tạo/sửa */
    @NotBlank(message = "Tiêu đề không được trống")
    private String title;

    /** Nội dung chi tiết — bắt buộc khi tạo/sửa */
    @NotBlank(message = "Nội dung không được trống")
    private String content;

    /** Thời điểm tạo — chỉ có trong response */
    private Instant createdAt;

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
