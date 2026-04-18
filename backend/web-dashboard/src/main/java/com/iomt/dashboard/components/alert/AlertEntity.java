package com.iomt.dashboard.components.alert;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.Instant;

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

    public Double bpm;

    public Double spo2;

    @Field("body_temp")
    public Double bodyTemp;

    @Field("gsr_adc")
    public Double gsrAdc;

    public Double confidence;

    @Field("mac_address")
    public String macAddress;
}
