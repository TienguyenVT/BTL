const { MongoClient } = require('mongodb');

/**
 * Normalize all datalake_raw records so that the final_result view
 * outputs documents in the canonical form:
 * {
 *   source, device_id, mac_address, timestamp,
 *   data_quality: "normalized", schema_version: "1.3",
 *   ingested_at: Date,
 *   bpm, spo2, body_temp, gsr_adc, room_temp, humidity,
 *   label, confidence
 * }
 */
async function main() {
    const c = new MongoClient('mongodb://127.0.0.1:27017');
    await c.connect();
    const db = c.db('iomt_health_monitor');
    const coll = db.collection('datalake_raw');

    console.log('=== Starting normalization of datalake_raw ===\n');

    // ------------------------------------------------------------------
    // 1. Fix MAC address: lowercase → uppercase
    // ------------------------------------------------------------------
    console.log('--- Step 1: Normalize MAC addresses to UPPERCASE ---');

    // Map known lowercase MACs to uppercase
    const macMapping = {
        '1c:db:d4:bb:44:09': '1C:DB:D4:BB:44:09',
        '4a:b2:01:c3:4d:10': '4A:B2:01:C3:4D:10',
        '2c:3e:5f:8a:1b:22': '2C:3E:5F:8A:1B:22',
        '9c:63:1a:5f:8d:99': '9C:63:1A:5F:8D:99',
        '3f:28:6d:4c:7a:88': '3F:28:6D:4C:7A:88',
        '8b:71:2d:6e:9f:33': '8B:71:2D:6E:9F:33',
        '6a:54:8c:1e:3b:77': '6A:54:8C:1E:3B:77',
        '1d:9c:3e:7f:0a:55': '1D:9C:3E:7F:0A:55',
        '5e:47:9b:2c:6f:44': '5E:47:9B:2C:6F:44',
        '7b:85:3d:6a:1c:aa': '7B:85:3D:6A:1C:AA',
        '3c:0f:02:cd:2c:88': '3C:0F:02:CD:2C:88',
    };

    for (const [lower, upper] of Object.entries(macMapping)) {
        // Update top-level mac_address
        const r1 = await coll.updateMany(
            { mac_address: lower },
            { $set: { mac_address: upper } }
        );
        // Update sensor.mac_address
        const r2 = await coll.updateMany(
            { "sensor.mac_address": lower },
            { $set: { "sensor.mac_address": upper } }
        );
        // Update raw_payload.mac_address
        const r3 = await coll.updateMany(
            { "raw_payload.mac_address": lower },
            { $set: { "raw_payload.mac_address": upper } }
        );
        if (r1.modifiedCount > 0 || r2.modifiedCount > 0 || r3.modifiedCount > 0) {
            console.log(`  ${lower} → ${upper}: top=${r1.modifiedCount}, sensor=${r2.modifiedCount}, raw=${r3.modifiedCount}`);
        }
    }

    // ------------------------------------------------------------------
    // 2. Fix empty MAC addresses (device_id = esp32_iot_health_01)
    // ------------------------------------------------------------------
    console.log('\n--- Step 2: Fix empty MAC addresses ---');
    const emptyMacResult = await coll.updateMany(
        { mac_address: '', device_id: 'esp32_iot_health_01' },
        { $set: { 
            mac_address: '1C:DB:D4:BB:44:09',
            "sensor.mac_address": '1C:DB:D4:BB:44:09',
            "raw_payload.mac_address": '1C:DB:D4:BB:44:09'
        }}
    );
    console.log(`  Fixed ${emptyMacResult.modifiedCount} records with empty MAC`);

    // ------------------------------------------------------------------
    // 3. Fix null humidity: set sensor.dht11_humidity from raw_payload
    //    or set to 0 if not available
    // ------------------------------------------------------------------
    console.log('\n--- Step 3: Fix null humidity records ---');
    // First try to fill from raw_payload.dht11_humidity
    const humFromRaw = await coll.updateMany(
        { 
            "sensor.dht11_humidity": { $exists: false },
            "raw_payload.dht11_humidity": { $exists: true, $ne: null }
        },
        [{ $set: { "sensor.dht11_humidity": "$raw_payload.dht11_humidity" } }]
    );
    console.log(`  Filled humidity from raw_payload: ${humFromRaw.modifiedCount} records`);

    // For v1.1 records that don't have dht11_humidity at all, set null explicitly
    // (they were imported data without DHT11 sensor)
    // Note: These will show as null in final_result view, which is acceptable

    // ------------------------------------------------------------------
    // 4. Normalize data_quality → "normalized"
    // ------------------------------------------------------------------
    console.log('\n--- Step 4: Set data_quality = "normalized" ---');
    const dqResult = await coll.updateMany(
        { data_quality: { $ne: 'normalized' } },
        { $set: { data_quality: 'normalized' } }
    );
    console.log(`  Updated ${dqResult.modifiedCount} records`);

    // ------------------------------------------------------------------
    // 5. Normalize schema_version → "1.3"
    // ------------------------------------------------------------------
    console.log('\n--- Step 5: Set schema_version = "1.3" ---');
    const svResult = await coll.updateMany(
        { schema_version: { $ne: '1.3' } },
        { $set: { schema_version: '1.3' } }
    );
    console.log(`  Updated ${svResult.modifiedCount} records`);

    // ------------------------------------------------------------------
    // 6. Ensure source = "mqtt_esp32" for all records
    // ------------------------------------------------------------------
    console.log('\n--- Step 6: Ensure source = "mqtt_esp32" ---');
    const srcResult = await coll.updateMany(
        { source: { $ne: 'mqtt_esp32' } },
        { $set: { source: 'mqtt_esp32' } }
    );
    console.log(`  Updated ${srcResult.modifiedCount} records`);

    // ------------------------------------------------------------------
    // 7. Fix records with null prediction (40 records excluded from view)
    //    Set prediction.label = "Unknown" so they appear in view
    // ------------------------------------------------------------------
    console.log('\n--- Step 7: Fix null prediction records ---');
    const nullPred = await coll.updateMany(
        { $or: [
            { "prediction.label": { $exists: false } },
            { "prediction.label": null },
            { prediction: null }
        ]},
        { $set: { 
            "prediction": { label: "Unknown", confidence: 0 }
        }}
    );
    console.log(`  Fixed ${nullPred.modifiedCount} records with null prediction`);

    // ------------------------------------------------------------------
    // 8. Sync sensor.mac_address with top-level mac_address where mismatched
    // ------------------------------------------------------------------
    console.log('\n--- Step 8: Sync sensor.mac_address with top-level ---');
    const syncMac = await coll.updateMany(
        { $expr: { $ne: ["$mac_address", "$sensor.mac_address"] } },
        [{ $set: { "sensor.mac_address": "$mac_address" } }]
    );
    console.log(`  Synced ${syncMac.modifiedCount} records`);

    // ------------------------------------------------------------------
    // 9. Also normalize realtime_health_data collection
    // ------------------------------------------------------------------
    console.log('\n--- Step 9: Normalize realtime_health_data ---');
    const rtColl = db.collection('realtime_health_data');

    // Fix MAC addresses in realtime_health_data
    for (const [lower, upper] of Object.entries(macMapping)) {
        const r = await rtColl.updateMany(
            { mac_address: lower },
            { $set: { mac_address: upper } }
        );
        if (r.modifiedCount > 0) {
            console.log(`  MAC ${lower} → ${upper}: ${r.modifiedCount} records`);
        }
    }
    const rtEmptyMac = await rtColl.updateMany(
        { mac_address: '', device_id: 'esp32_iot_health_01' },
        { $set: { mac_address: '1C:DB:D4:BB:44:09' } }
    );
    if (rtEmptyMac.modifiedCount > 0) {
        console.log(`  Fixed ${rtEmptyMac.modifiedCount} empty MACs in realtime_health_data`);
    }

    // ------------------------------------------------------------------
    // VERIFY
    // ------------------------------------------------------------------
    console.log('\n=== VERIFICATION ===');
    console.log('\n--- final_result sample (latest 3) ---');
    const latest = await db.collection('final_result').find({}).sort({ ingested_at: -1 }).limit(3).toArray();
    latest.forEach(r => console.log(JSON.stringify(r, null, 2)));

    console.log('\n--- final_result total ---');
    console.log(`  ${await db.collection('final_result').countDocuments({})} records`);

    console.log('\n--- Distinct MACs ---');
    const macs = await db.collection('final_result').distinct('mac_address');
    console.log(`  ${JSON.stringify(macs)}`);

    console.log('\n--- Null checks ---');
    const nullChecks = {
        'null humidity': { humidity: null },
        'null bpm': { bpm: null },
        'null spo2': { spo2: null },
        'empty mac': { mac_address: { $in: ['', null] } },
        'null label': { label: null },
        'data_quality != normalized': { data_quality: { $ne: 'normalized' } },
        'schema_version != 1.3': { schema_version: { $ne: '1.3' } },
    };
    for (const [name, query] of Object.entries(nullChecks)) {
        const count = await db.collection('final_result').countDocuments(query);
        console.log(`  ${name}: ${count}`);
    }

    console.log('\n--- Distinct labels ---');
    const labels = await db.collection('final_result').distinct('label');
    console.log(`  ${JSON.stringify(labels)}`);

    console.log('\n=== Normalization complete! ===');

    await c.close();
}
main().catch(console.error);
