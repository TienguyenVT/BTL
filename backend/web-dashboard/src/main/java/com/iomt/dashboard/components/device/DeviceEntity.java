package com.iomt.dashboard.components.device;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "devices")
public class DeviceEntity {

    @Id
    public String id;

    @Field("user_id")
    public String userId;

    @Indexed(unique = true)
    @Field("mac_address")
    public String macAddress;

    @Field("name")
    public String name;

    @Field("created_at")
    public Instant createdAt;
}
