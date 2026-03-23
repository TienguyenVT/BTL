package com.iomt.dashboard.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Security configuration tối giản — cho phép test Diary trước.
 *
 * HIỆN TẠI (test):
 *   - /api/**  → permitAll() — ai cũng gọi được
 *
 * KHI THÊM AUTH (sau):
 *   - /api/auth/**  → permitAll()
 *   - /api/**       → authenticated() — cần JWT
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // Tắt CSRF (API stateless)
            .csrf(AbstractHttpConfigurer::disable)

            // Phân quyền
            .authorizeHttpRequests(auth -> auth
                // Cho phép tất cả API — test trước
                .requestMatchers("/api/**").permitAll()
                // Swagger/OpenAPI docs
                .requestMatchers("/swagger-ui/**", "/v3/api-docs/**").permitAll()
                // Health check
                .requestMatchers("/").permitAll()
                // Mọi thứ còn lại
                .anyRequest().permitAll()
            );

        return http.build();
    }

    /** BCrypt encoder — dùng cho auth module */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
