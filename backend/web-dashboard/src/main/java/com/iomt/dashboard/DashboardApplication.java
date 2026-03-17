package com.iomt.dashboard;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Entry Point - Spring Boot Application.
 * <p>
 * Module 2: Web Dashboard - Cung cấp RESTful API cho Frontend.
 * Chỉ ĐỌC dữ liệu sạch từ MongoDB collection "clean_health_data"
 * (do Python iot-ingestion module ghi vào).
 * </p>
 *
 * Chạy: mvn spring-boot:run
 * Swagger UI: http://localhost:8080/swagger-ui.html
 */
@SpringBootApplication
public class DashboardApplication {

    public static void main(String[] args) {
        SpringApplication.run(DashboardApplication.class, args);
    }
}
