package com.iomt.dashboard.controller;

import com.iomt.dashboard.dto.HealthDataResponse;
import com.iomt.dashboard.service.DashboardService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

/**
 * Dashboard REST Controller - API endpoints cho Frontend.
 * <p>
 * Base path: /api/health
 * </p>
 *
 * Endpoints:
 *   GET /api/health/latest?userId=xxx     → Dữ liệu mới nhất (realtime)
 *   GET /api/health/history?userId=xxx    → Lịch sử theo thời gian
 *   GET /api/health/recent?userId=xxx     → N bản ghi gần nhất
 */
@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
@Tag(name = "Health Data", description = "API quản lý dữ liệu sức khỏe IoMT")
public class DashboardController {

    private final DashboardService dashboardService;

    /**
     * GET /api/health/latest - Lấy dữ liệu sức khỏe mới nhất.
     * Dùng cho: Dashboard realtime hiển thị chỉ số hiện tại.
     *
     * @param userId ID người dùng (VD: "Nguyen_Van")
     */
    @GetMapping("/latest")
    @Operation(summary = "Lấy dữ liệu mới nhất", description = "Trả về bản ghi sức khỏe gần nhất của user")
    public ResponseEntity<HealthDataResponse> getLatest(
            @Parameter(description = "ID người dùng") @RequestParam String userId) {

        HealthDataResponse data = dashboardService.getLatestByUser(userId);

        if (data == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(data);
    }

    /**
     * GET /api/health/history - Lấy lịch sử dữ liệu theo khoảng thời gian.
     * Dùng cho: Biểu đồ HealthChart trên Frontend.
     *
     * @param userId ID người dùng
     * @param hours  Số giờ trở về trước (mặc định 24h)
     */
    @GetMapping("/history")
    @Operation(summary = "Lấy lịch sử dữ liệu", description = "Trả về dữ liệu trong khoảng thời gian chỉ định")
    public ResponseEntity<List<HealthDataResponse>> getHistory(
            @Parameter(description = "ID người dùng") @RequestParam String userId,
            @Parameter(description = "Số giờ trở về trước") @RequestParam(defaultValue = "24") int hours) {

        Instant to = Instant.now();
        Instant from = to.minus(hours, ChronoUnit.HOURS);

        List<HealthDataResponse> history = dashboardService.getHistory(userId, from, to);
        return ResponseEntity.ok(history);
    }

    /**
     * GET /api/health/recent - Lấy N bản ghi gần nhất.
     * Dùng cho: Bảng dữ liệu gần đây trên Dashboard.
     *
     * @param userId ID người dùng
     * @param limit  Số bản ghi tối đa (mặc định 20)
     */
    @GetMapping("/recent")
    @Operation(summary = "Lấy dữ liệu gần đây", description = "Trả về N bản ghi mới nhất")
    public ResponseEntity<List<HealthDataResponse>> getRecent(
            @Parameter(description = "ID người dùng") @RequestParam String userId,
            @Parameter(description = "Số bản ghi tối đa") @RequestParam(defaultValue = "20") int limit) {

        List<HealthDataResponse> recent = dashboardService.getRecent(userId, limit);
        return ResponseEntity.ok(recent);
    }
}
