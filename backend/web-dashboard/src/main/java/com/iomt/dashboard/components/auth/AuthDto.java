package com.iomt.dashboard.components.auth;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuthDto {

    public String email;
    public String password;
    public String name;

    public String id;
    public String message;

    public void setMessage(String msg) {
        this.message = msg;
    }
}
