package com.iomt.dashboard.components.health;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * DTO: Bản ghi Stress/Fever từ final_result, có phân trang.
 * Dùng cho AlertsPage — truy vấn trực tiếp final_result thay vì collection alerts.
 *
 * Chứa danh sách records + metadata phân trang.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class FeverStressRecordDto {

    /** Danh sách bản ghi trong trang hiện tại */
    public List<SessionDto.HealthRecordDto> records;

    /** Tổng số bản ghi (để tính tổng số trang) */
    public long totalCount;

    /** Số trang hiện tại (0-based) */
    public int page;

    /** Kích thước mỗi trang */
    public int size;

    /** Tổng số trang */
    public int totalPages;
}
