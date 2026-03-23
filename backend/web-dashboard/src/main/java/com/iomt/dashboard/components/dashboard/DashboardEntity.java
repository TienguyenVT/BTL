package com.iomt.dashboard.components.dashboard;

/**
 * ============================================================
 * DashboardEntity — Entity: Du lieu suc khoe (tu ESP32)
 * ============================================================
 *
 * COLLECTION: "realtime_health_data"
 *
 * CAC TRUONG:
 *    - id             : ObjectId
 *    - userId         : ID nguoi dung
 *    - deviceId       : ID thiet bi ESP32
 *    - timestamp      : Thoi diem do
 *    - bpm            : Nhip tim (beats per minute)
 *    - spo2           : Do bao hoa oxy (%)
 *    - bodyTemp       : Nhiet do co the (°C)
 *    - gsrAdc         : Dien tro da (ADC value)
 *    - extTempC       : Nhiet do moi truong (°C)
 *    - extHumidityPct : Do am moi truong (%)
 *    - label          : Phan loai: Normal | Stress | Fever
 *    - timeSlot       : Khoang thoi gian: Morning | Afternoon | Evening
 *
 * CRUD: Read only (TUYET DOI khong sua / xoa du lieu y te)
 */
public class DashboardEntity {

    // @Id
    // private String id;

    // @Field("user_id")
    // private String userId;

    // @Field("device_id")
    // private String deviceId;

    // @Field("timestamp")
    // private Instant timestamp;

    // @Field("bpm")
    // private Double bpm;

    // @Field("spo2")
    // private Double spo2;

    // @Field("body_temp")
    // private Double bodyTemp;

    // @Field("gsr_adc")
    // private Double gsrAdc;

    // @Field("ext_temp_c")
    // private Double extTempC;

    // @Field("ext_humidity_pct")
    // private Double extHumidityPct;

    // @Field("label")
    // private String label;

    // @Field("time_slot")
    // private String timeSlot;
}
