package com.iomt.dashboard.components.auth;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO: Truyen nhan du lieu Auth (dang ky / dang nhap).
 *
 * Request (dang ky):
 *    - email    : bat buoc
 *    - password : bat buoc
 *    - name     : bat buoc
 *
 * Request (dang nhap):
 *    - email    : bat buoc
 *    - password : bat buoc
 *
 * Response:
 *    - id      : tra ve sau khi dang ky / dang nhap thanh cong
 *    - name    : tra ve sau khi dang ky / dang nhap thanh cong
 *    - message : thong bao thanh cong hoac loi
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuthDto {

    // --- Request fields ---
    public String email;
    public String password;
    public String name;

    // --- Response fields ---
    public String id;
    public String message;

    public void setMessage(String msg) {
        this.message = msg;
    }
}
