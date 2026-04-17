const { MongoClient } = require('mongodb');

async function main() {
    const client = new MongoClient("mongodb://127.0.0.1:27017");
    await client.connect();
    const db = client.db("iomt_health_monitor");

    console.log("=== 1. MAC addresses in 'devices' collection ===");
    const devices = await db.collection("devices").find({}, { projection: { mac_address: 1, name: 1, user_id: 1 } }).toArray();
    devices.forEach(d => {
        console.log(`  Device: name="${d.name}", mac_address="${d.mac_address}", user_id="${d.user_id}", _id="${d._id}"`);
        // Show actual bytes to detect invisible chars
        const macBytes = d.mac_address ? [...d.mac_address].map(c => c.charCodeAt(0).toString(16).padStart(2,'0')).join(' ') : 'null';
        console.log(`    char codes: [${macBytes}]`);
        console.log(`    length: ${(d.mac_address || '').length}`);
    });

    console.log("\n=== 2. Distinct MAC addresses in 'final_result' collection ===");
    const frMacs = await db.collection("final_result").distinct("mac_address");
    frMacs.forEach(mac => {
        const macBytes = mac ? [...mac].map(c => c.charCodeAt(0).toString(16).padStart(2,'0')).join(' ') : 'null';
        console.log(`  mac_address="${mac}"`);
        console.log(`    char codes: [${macBytes}]`);
        console.log(`    length: ${(mac || '').length}`);
    });

    console.log("\n=== 3. Comparison (exact, upper, lower) ===");
    for (const d of devices) {
        const macRaw = d.mac_address || '';
        const macUpper = macRaw.trim().toUpperCase();
        const macLower = macRaw.trim().toLowerCase();

        const countRaw = await db.collection("final_result").countDocuments({ mac_address: macRaw });
        const countUpper = await db.collection("final_result").countDocuments({ mac_address: macUpper });
        const countLower = await db.collection("final_result").countDocuments({ mac_address: macLower });
        
        console.log(`  Device "${d.name}" (id=${d._id}):`);
        console.log(`    mac_address raw   = "${macRaw}" => ${countRaw} records in final_result`);
        console.log(`    mac_address UPPER = "${macUpper}" => ${countUpper} records in final_result`);
        console.log(`    mac_address lower = "${macLower}" => ${countLower} records in final_result`);
    }

    // Also check what field names the final_result uses for mac
    console.log("\n=== 4. Sample records from final_result (last 5) ===");
    const samples = await db.collection("final_result").find({}).sort({ _id: -1 }).limit(5)
        .project({ mac_address: 1, device_id: 1, timestamp: 1, label: 1 }).toArray();
    samples.forEach(s => console.log(`  ${JSON.stringify(s)}`));

    // Check if final_result also has device_id field
    console.log("\n=== 5. Distinct 'device_id' in final_result ===");
    const frDeviceIds = await db.collection("final_result").distinct("device_id");
    console.log(`  device_id values: ${JSON.stringify(frDeviceIds)}`);

    // Check system.views to understand final_result definition
    console.log("\n=== 6. system.views (check if final_result is a view) ===");
    const views = await db.collection("system.views").find({}).toArray();
    views.forEach(v => console.log(`  ${JSON.stringify(v)}`));

    console.log(`\n=== 7. Total records in final_result: ${await db.collection("final_result").countDocuments({})} ===`);

    await client.close();
}
main().catch(console.error);
