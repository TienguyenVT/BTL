package com.iomt.dashboard.components.alert;

/**
 * ============================================================
 * AlertEntity — Entity: Canh bao suc khoe
 * ============================================================
 *
 * COLLECTION: "alerts"
 *
 * CAC TRUONG:
 *    - id        : ObjectId
 *    - userId    : ID nguoi dung
 *    - label     : Loai: "Stress" | "Fever"
 *    - message   : Noi dung chi tiet
 *    - timestamp : Thoi diem xay ra
 *    - isRead    : Da doc chua (default: false)
 *
 * VI DU DOCUMENT:
 *    {
 *        "_id": ObjectId("..."),
 *        "userId": "65f...",
 *        "label": "Stress",
 *        "message": "Phat hien trang thai Stress luc 10:00 ngay 23/03/2026",
 *        "timestamp": ISODate("2026-03-23T10:00:00Z"),
 *        "isRead": false
 *    }
 *
 * CRUD: Read + Delete
 *    Tao Alert: tu dong boi he thong (AI), khong co API tao.
 */
public class AlertEntity {

    // @Id
    // private String id;

    // @Field("user_id")
    // private String userId;

    // @Field("label")
    // private String label;

    // @Field("message")
    // private String message;

    // @Field("timestamp")
    // private Instant timestamp;

    // @Field("is_read")
    // private Boolean isRead;
}
