package com.iomt.dashboard.components.device;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DeviceDto {

    public String id;
    public String macAddress;
    public String name;
    public Instant createdAt;
    public String message;
}
