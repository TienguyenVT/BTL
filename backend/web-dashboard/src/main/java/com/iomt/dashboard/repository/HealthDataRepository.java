package com.iomt.dashboard.repository;

import com.iomt.dashboard.document.HealthDataDocument;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Spring Data MongoDB Repository - Truy vấn dữ liệu sức khỏe.
 * <p>
 * Chỉ cung cấp các phương thức ĐỌC (read-only).
 * Module này KHÔNG ghi dữ liệu vào MongoDB.
 * </p>
 *
 * Spring Data tự động tạo implementation dựa trên tên method.
 */
@Repository
public interface HealthDataRepository extends MongoRepository<HealthDataDocument, String> {

    /**
     * Lấy bản ghi mới nhất theo device_id.
     * Dùng cho: Dashboard realtime hiển thị chỉ số hiện tại.
     */
    Optional<HealthDataDocument> findTopByDeviceIdOrderByTimestampDesc(String deviceId);

    /**
     * Lấy bản ghi mới nhất theo user_id.
     * Dùng cho: Dashboard realtime của user.
     */
    Optional<HealthDataDocument> findTopByUserIdOrderByTimestampDesc(String userId);

    /**
     * Lấy lịch sử dữ liệu của user trong khoảng thời gian.
     * Dùng cho: Biểu đồ lịch sử (HealthChart).
     */
    List<HealthDataDocument> findByUserIdAndTimestampBetweenOrderByTimestampAsc(
            String userId, Instant from, Instant to);

    /**
     * Lấy N bản ghi mới nhất của user (có phân trang).
     * Dùng cho: Bảng dữ liệu gần đây.
     */
    List<HealthDataDocument> findByUserIdOrderByTimestampDesc(String userId, Pageable pageable);

    /**
     * Lấy dữ liệu theo nhãn sức khỏe (Normal/Stress/Fever).
     * Dùng cho: Thống kê phân bố trạng thái.
     */
    List<HealthDataDocument> findByUserIdAndLabel(String userId, String label);

    /**
     * Đếm số bản ghi theo user_id.
     * Dùng cho: Thống kê tổng quan.
     */
    long countByUserId(String userId);
}
