package com.iomt.dashboard.components.profile;

/**
 * ============================================================
 * ProfileEntity — Entity: Thong tin sinh truc hoc
 * ============================================================
 *
 * COLLECTION: "profiles"
 *
 * CAC TRUONG:
 *    - userId   : ID nguoi dung (unique, khong co @Id)
 *    - age      : Tuoi (nullable)
 *    - height   : Chieu cao cm (nullable)
 *    - weight   : Can nang kg (nullable)
 *    - updatedAt: Thoi diem cap nhat
 *
 * VI DU DOCUMENT:
 *    {
 *        "userId": "65f...",
 *        "age": 25,
 *        "height": 170.5,
 *        "weight": 65.0,
 *        "updatedAt": ISODate("2026-03-23T10:00:00Z")
 *    }
 *
 * CRUD: Read (GET) + Update (PUT)
 *    Khong co Delete vi profile la thong tin co ban.
 */
public class ProfileEntity {

    // @Field("user_id")
    // private String userId;   <- unique index

    // @Field("age")
    // private Integer age;

    // @Field("height")
    // private Double height;

    // @Field("weight")
    // private Double weight;

    // @Field("updated_at")
    // private Instant updatedAt;
}
