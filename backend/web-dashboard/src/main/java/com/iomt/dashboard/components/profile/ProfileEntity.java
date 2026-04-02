package com.iomt.dashboard.components.profile;

import lombok.Data;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * Entity: Thong tin sinh truc hoc cua nguoi dung.
 * Collection: "profiles"
 *
 * Cac truong:
 *    - userId   : ID nguoi dung (unique, khong co @Id)
 *    - age      : Tuoi (nullable)
 *    - height   : Chieu cao cm (nullable)
 *    - weight   : Can nang kg (nullable)
 *    - updatedAt: Thoi diem cap nhat gan nhat
 */
@Data
@Document(collection = "profiles")
public class ProfileEntity {

    @Field("user_id")
    public String userId;

    public Integer age;

    public Double height;

    public Double weight;

    @Field("updated_at")
    public Instant updatedAt;
}
