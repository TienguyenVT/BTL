package com.iomt.dashboard.components.auth;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

/**
 * Entity: Tai khoan nguoi dung.
 * Collection: "users"
 *
 * Cac truong:
 *    - id       : ObjectId tu dong
 *    - email    : Email (unique)
 *    - password : Mat khau (plain text, chi de demo)
 *    - name     : Ten nguoi dung
 *    - createdAt: Thoi diem tao tai khoan
 */
@Data
@Document(collection = "users")
public class AuthEntity {

    @Id
    public String id;

    @Indexed(unique = true)
    public String email;

    public String password;

    public String name;

    public Instant createdAt;
}
