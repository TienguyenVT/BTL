package com.iomt.dashboard.components.alert;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AlertDto {

    public String id;
    public String label;
    public String message;
    public Instant timestamp;
    public Boolean isRead;

    public Double bpm;
    public Double spo2;
    public Double bodyTemp;
    public Double gsrAdc;
    public Double confidence;
    public String macAddress;
}
