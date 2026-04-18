package com.iomt.dashboard.components.profile;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProfileDto {

    public String userId;
    public Integer age;
    public Double height;
    public Double weight;
    public Double bmi;
    public Instant updatedAt;
}
