package com.iomt.dashboard.service;

import com.iomt.dashboard.document.HealthDataDocument;
import com.iomt.dashboard.dto.HealthDataResponse;
import com.iomt.dashboard.repository.HealthDataRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Dashboard Service - Business Logic Layer (READ-ONLY).
 * <p>
 * Module này chỉ ĐỌC dữ liệu sạch từ MongoDB.
 * Dữ liệu được ghi bởi Python iot-ingestion module.
 * </p>
 *
 * Chức năng:
 *   - Lấy dữ liệu mới nhất (realtime dashboard)
 *   - Lấy lịch sử theo khoảng thời gian (biểu đồ)
 *   - Lấy N bản ghi gần nhất (bảng dữ liệu)
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class DashboardService {

    private final HealthDataRepository repository;

    /**
     * Lấy bản ghi mới nhất của user (cho Dashboard realtime).
     *
     * @param userId ID người dùng
     * @return HealthDataResponse hoặc null nếu không có dữ liệu
     */
    public HealthDataResponse getLatestByUser(String userId) {
        log.debug("Lấy dữ liệu mới nhất cho user: {}", userId);
        return repository.findTopByUserIdOrderByTimestampDesc(userId)
                .map(this::toResponse)
                .orElse(null);
    }

    /**
     * Lấy lịch sử dữ liệu theo khoảng thời gian (cho biểu đồ HealthChart).
     *
     * @param userId ID người dùng
     * @param from   Thời điểm bắt đầu
     * @param to     Thời điểm kết thúc
     * @return Danh sách dữ liệu sắp xếp theo thời gian tăng dần
     */
    public List<HealthDataResponse> getHistory(String userId, Instant from, Instant to) {
        log.debug("Lấy lịch sử user: {} từ {} đến {}", userId, from, to);
        return repository.findByUserIdAndTimestampBetweenOrderByTimestampAsc(userId, from, to)
                .stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    /**
     * Lấy N bản ghi gần nhất của user (cho bảng dữ liệu).
     *
     * @param userId ID người dùng
     * @param limit  Số bản ghi tối đa
     * @return Danh sách dữ liệu mới nhất trước
     */
    public List<HealthDataResponse> getRecent(String userId, int limit) {
        log.debug("Lấy {} bản ghi gần nhất cho user: {}", limit, userId);
        return repository.findByUserIdOrderByTimestampDesc(userId, PageRequest.of(0, limit))
                .stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    /**
     * Chuyển đổi Document → DTO Response.
     * Tách biệt internal model và API response.
     */
    private HealthDataResponse toResponse(HealthDataDocument doc) {
        return HealthDataResponse.builder()
                .deviceId(doc.getDeviceId())
                .userId(doc.getUserId())
                .timestamp(doc.getTimestamp())
                .bpm(doc.getBpm())
                .spo2(doc.getSpo2())
                .bodyTemp(doc.getBodyTemp())
                .gsrAdc(doc.getGsrAdc())
                .extTempC(doc.getExtTempC())
                .extHumidityPct(doc.getExtHumidityPct())
                .label(doc.getLabel())
                .timeSlot(doc.getTimeSlot())
                .build();
    }
}
