const { MongoClient } = require('mongodb');

async function main() {
    const client = new MongoClient('mongodb://127.0.0.1:27017');
    await client.connect();
    const db = client.db('iomt_health_monitor');

    // Check if mac_address field exists in final_result
    const latest = await db.collection('final_result').findOne({}, { sort: { timestamp: -1 } });
    console.log('=== Latest final_result record (ALL fields) ===');
    console.log(JSON.stringify(latest, null, 2));

    // Check field names
    console.log('\n=== All field names ===');
    if (latest) Object.keys(latest).forEach(k => console.log('  ', k, ':', JSON.stringify(latest[k])));

    // Check if there's a macAddress field (different from mac_address)
    const hasMacAddress = latest && 'macAddress' in latest;
    const hasMac = latest && 'mac_address' in latest;
    console.log('\nHas macAddress field:', hasMacAddress);
    console.log('Has mac_address field:', hasMac);

    // Try case-insensitive search for the MAC
    const exactMatch = await db.collection('final_result').countDocuments({ mac_address: '1C:DB:D4:BB:44:09' });
    const lowerMatch = await db.collection('final_result').countDocuments({ mac_address: '1c:db:d4:bb:44:09' });
    console.log('\nRecords with MAC "1C:DB:D4:BB:44:09" (exact uppercase):', exactMatch);
    console.log('Records with MAC "1c:db:d4:bb:44:09" (lowercase):', lowerMatch);

    // Check if the query in Java uses case-insensitive
    // Query in Java: Criteria.where("mac_address").in(targetMacs)
    // where targetMacs contains "1c:db:d4:bb:44:09" (from device MAC, lowercase)
    // But final_result might store as "1C:DB:D4:BB:44:09" (uppercase)
    console.log('\n=== Sample records with their MAC casing ===');
    const samples = await db.collection('final_result').find({}).sort({ timestamp: -1 }).limit(10).toArray();
    samples.forEach(r => console.log('  mac_address:', r.mac_address, '| timestamp:', r.timestamp));

    await client.close();
}
main();
