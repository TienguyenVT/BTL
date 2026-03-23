package com.iomt.dashboard.components.device;

/**
 * ============================================================
 * DeviceEntity — Entity: Thiet bi ESP32
 * ============================================================
 *
 * COLLECTION: "devices"
 *
 * CAC TRUONG:
 *    - id          : ObjectId
 *    - userId      : ID nguoi dung
 *    - macAddress  : Dia chi MAC ESP32 (unique)
 *    - name        : Ten thiet bi (optional)
 *    - createdAt   : Thoi diem dang ky
 *
 * VI DU DOCUMENT:
 *    {
 *        "_id": ObjectId("..."),
 *        "userId": "65f...",
 *        "macAddress": "AA:BB:CC:DD:EE:FF",
 *        "name": "Thiet bi nha tien",
 *        "createdAt": ISODate("2026-03-23T10:00:00Z")
 *    }
 *
 * CRUD: Create + Read + Delete
 */
public class DeviceEntity {

    // @Id
    // private String id;

    // @Field("user_id")
    // private String userId;

    // @Field("mac_address")
    // @Indexed(unique = true)
    // private String macAddress;

    // @Field("name")
    // private String name;

    // @Field("created_at")
    // private Instant createdAt;
}
