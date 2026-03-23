package com.iomt.dashboard.components.auth;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuthDto {

    // ── Register request ──────────────────────────────────────────
    @NotBlank(message = "Email la bat buoc")
    @Email(message = "Email khong dung dinh dang")
    private String email;

    @NotBlank(message = "Mat khau la bat buoc")
    @Size(min = 6, message = "Mat khau phai it nhat 6 ky tu")
    private String password;

    private String name;  // nullable for login

    // ── Response fields ───────────────────────────────────────────
    private String id;
    private String token;  // null khi register, co khi login

    // ── Factory methods ───────────────────────────────────────────
    public static AuthDto fromEntity(AuthEntity entity, String token) {
        AuthDto dto = new AuthDto();
        dto.setId(entity.getId());
        dto.setEmail(entity.getEmail());
        dto.setName(entity.getName());
        dto.setToken(token);
        return dto;
    }

    public static AuthDto fromEntity(AuthEntity entity) {
        return fromEntity(entity, null);
    }
}
