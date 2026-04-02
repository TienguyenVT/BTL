package com.iomt.dashboard.components.profile;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO: Tra ve thong tin profile + BMI tinh dong.
 *
 * Response:
 *    - userId    : ID nguoi dung
 *    - age       : Tuoi
 *    - height    : Chieu cao (cm)
 *    - weight    : Can nang (kg)
 *    - bmi       : Chi so BMI (tinh dong)
 *    - updatedAt : Thoi diem cap nhat
 */
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
