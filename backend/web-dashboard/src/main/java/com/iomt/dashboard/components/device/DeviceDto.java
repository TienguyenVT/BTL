package com.iomt.dashboard.components.device;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO: Thong tin thiet bi.
 *
 * Request (tao moi):
 *    - macAddress : bat buoc
 *    - name       : tuy chon
 *
 * Response:
 *    - id         : ObjectId
 *    - macAddress : dia chi MAC
 *    - name       : ten thiet bi
 *    - createdAt  : thoi diem tao
 *    - message    : thong bao loi (neu co)
 */
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
