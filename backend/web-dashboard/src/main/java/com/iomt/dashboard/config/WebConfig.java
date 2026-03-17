package com.iomt.dashboard.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Cấu hình CORS (Cross-Origin Resource Sharing).
 * <p>
 * Cho phép Frontend (React, chạy ở port khác) gọi API Backend.
 * Trong production nên giới hạn lại origin cụ thể.
 * </p>
 */
@Configuration
public class WebConfig {

    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")               // Áp dụng cho tất cả API
                        .allowedOrigins(
                            "http://localhost:5173",          // Vite dev server
                            "http://localhost:3000"           // CRA dev server
                        )
                        .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                        .allowedHeaders("*")
                        .allowCredentials(true)
                        .maxAge(3600);                        // Cache preflight 1 giờ
            }
        };
    }
}
