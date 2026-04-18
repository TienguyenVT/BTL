package com.iomt.dashboard.components.profile;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

@Data
@Document(collection = "profiles")
public class ProfileEntity {

    @Id
    @Field("user_id")
    public String userId;

    public Integer age;

    public Double height;

    public Double weight;

    @Field("updated_at")
    public Instant updatedAt;
}
