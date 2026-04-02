package com.iomt.dashboard.components.alert;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO: Tra ve thong tin canh bao.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AlertDto {

    public String id;
    public String label;
    public String message;
    public Instant timestamp;
    public Boolean isRead;
}
