// ============================================================
// MongoDB Performance Optimization — BTL IoMT Dashboard
// Chạy: mongosh "mongodb://localhost:27017/iomt_health_monitor"
// ============================================================

// 1. Xem các collection hiện tại
print("=== Collections ===");
db.getCollectionNames().forEach(c => {
    const count = db.getCollection(c).countDocuments();
    const sample = db.getCollection(c).findOne();
    print(`  ${c}: ${count} docs`);
});

// 2. Kiểm tra indexes hiện tại
print("\n=== Current Indexes ===");
print("--- final_result ---");
db.final_result.getIndexes().forEach(idx => printjson(idx));
print("--- sessions ---");
db.sessions.getIndexes().forEach(idx => printjson(idx));
print("--- devices ---");
db.devices.getIndexes().forEach(idx => printjson(idx));

// 3. Xóa indexes cũ (nếu có)
print("\n=== Dropping old indexes ===");
try { db.final_result.dropIndex("mac_address_1_timestamp_-1"); print("dropped: mac_address_1_timestamp_-1"); } catch(e) {}
try { db.final_result.dropIndex("mac_address_1_timestamp_1"); print("dropped: mac_address_1_timestamp_1"); } catch(e) {}
try { db.final_result.dropIndex("timestamp_1"); print("dropped: timestamp_1"); } catch(e) {}
try { db.final_result.dropIndex("mac_address_1"); print("dropped: mac_address_1"); } catch(e) {}

// 4. Tạo indexes tối ưu cho final_result
// Index #1: mac_address + timestamp ASC — dùng cho findSessionRecords, getLiveSession records
print("\n=== Creating indexes for final_result ===");
db.final_result.createIndex(
    { "mac_address": 1, "timestamp": 1 },
    {
        name: "mac_timestamp_asc",
        background: true,
        partialFilterExpression: { "mac_address": { $exists: true } }
    }
);
print("Created: mac_address_1_timestamp_1 (ASC)");

// Index #2: mac_address + timestamp DESC — dùng cho getLiveSession tìm bản ghi mới nhất
db.final_result.createIndex(
    { "mac_address": 1, "timestamp": -1 },
    {
        name: "mac_timestamp_desc",
        background: true,
        partialFilterExpression: { "mac_address": { $exists: true } }
    }
);
print("Created: mac_address_1_timestamp_-1 (DESC)");

// Index #3: timestamp ASC — dùng cho rebuildSessions (full scan theo thời gian)
db.final_result.createIndex(
    { "timestamp": 1 },
    {
        name: "timestamp_asc",
        background: true
    }
);
print("Created: timestamp_1 (ASC)");

// Index #4: ingested_at DESC — dùng khi cần sort theo server time
db.final_result.createIndex(
    { "ingested_at": -1 },
    {
        name: "ingested_at_desc",
        background: true,
        partialFilterExpression: { "ingested_at": { $exists: true } }
    }
);
print("Created: ingested_at_-1 (DESC)");

// 5. Tạo indexes cho sessions collection
print("\n=== Creating indexes for sessions ===");
try { db.sessions.dropIndex("active_1_start_time_-1"); print("dropped: active_1_start_time_-1"); } catch(e) {}
try { db.sessions.dropIndex("start_time_-1"); print("dropped: start_time_-1"); } catch(e) {}
try { db.sessions.dropIndex("session_id_1"); print("dropped: session_id_1"); } catch(e) {}

db.sessions.createIndex(
    { "active": 1, "start_time": -1 },
    {
        name: "active_start_time",
        background: true
    }
);
print("Created: active_1_start_time_-1");

db.sessions.createIndex(
    { "start_time": -1 },
    {
        name: "start_time_desc",
        background: true
    }
);
print("Created: start_time_-1");

db.sessions.createIndex(
    { "session_id": 1 },
    {
        name: "session_id_unique",
        unique: true,
        background: true,
        partialFilterExpression: { "session_id": { $exists: true } }
    }
);
print("Created: session_id_1 (unique)");

// 6. Tạo indexes cho devices collection
print("\n=== Creating indexes for devices ===");
try { db.devices.dropIndex("user_id_1"); print("dropped: user_id_1"); } catch(e) {}
try { db.devices.dropIndex("mac_address_1"); print("dropped: mac_address_1"); } catch(e) {}

db.devices.createIndex(
    { "user_id": 1 },
    { name: "user_id_1", background: true }
);
print("Created: user_id_1");

db.devices.createIndex(
    { "mac_address": 1 },
    {
        name: "mac_address_unique",
        unique: true,
        background: true,
        partialFilterExpression: { "mac_address": { $exists: true } }
    }
);
print("Created: mac_address_1 (unique)");

// 7. Verify indexes
print("\n=== Final Indexes ===");
print("--- final_result ---");
db.final_result.getIndexes().forEach(idx => print(`  ${idx.name}: ${tojson(idx.key)}`));
print("--- sessions ---");
db.sessions.getIndexes().forEach(idx => print(`  ${idx.name}: ${tojson(idx.key)}`));
print("--- devices ---");
db.devices.getIndexes().forEach(idx => print(`  ${idx.name}: ${tojson(idx.key)}`));

// 8. Explain query — kiểm tra query plan cho getLiveSession pattern
print("\n=== Explain: getLiveSession latest query ===");
var expl = db.final_result.find(
    { "mac_address": { $in: ["1C:DB:D4:BB:44:09"] } }
).sort({ "timestamp": -1 }).limit(1).explain("executionStats");
print(`  Collection scan: ${expl.executionStats.totalDocsExamined} docs examined`);
print(`  Results returned: ${expl.executionStats.nReturned}`);
print(`  Index used: ${expl.executionStats.indexName}`);
print(`  Execution time: ${expl.executionStats.executionTimeMillis} ms`);

print("\n=== Explain: getLiveSession records window query ===");
expl = db.final_result.find(
    {
        "timestamp": { $gte: "2026:04:17 - 01:00:00" },
        "mac_address": { $in: ["1C:DB:D4:BB:44:09"] }
    }
).sort({ "timestamp": 1 }).explain("executionStats");
print(`  Collection scan: ${expl.executionStats.totalDocsExamined} docs examined`);
print(`  Results returned: ${expl.executionStats.nReturned}`);
print(`  Index used: ${expl.executionStats.indexName}`);
print(`  Execution time: ${expl.executionStats.executionTimeMillis} ms`);

print("\n=== Done ===");
