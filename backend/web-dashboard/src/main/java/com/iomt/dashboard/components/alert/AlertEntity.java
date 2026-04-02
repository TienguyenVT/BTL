package com.iomt.dashboard.components.alert;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

/**
 * Entity: Canh bao suc khoe tu dong.
 * Collection: "alerts"
 *
 * Cac truong:
 *    - id        : ObjectId
 *    - userId    : ID nguoi dung
 *    - label     : Loai: "Stress" | "Fever"
 *    - message   : Noi dung chi tiet
 *    - timestamp : Thoi diem xay ra
 *    - isRead    : Da doc chua (mac dinh: false)
 */
@Data
@Document(collection = "alerts")
public class AlertEntity {

    @Id
    public String id;

    @Field("user_id")
    public String userId;

    public String label;

    public String message;

    public Instant timestamp;

    @Field("is_read")
    public Boolean isRead;
}
