const { MongoClient } = require('mongodb');

async function main() {
    const client = new MongoClient("mongodb://127.0.0.1:27017");
    await client.connect();
    
    // List all databases
    const adminDb = client.db().admin();
    const dbList = await adminDb.listDatabases();
    console.log("=== All databases ===");
    for (const d of dbList.databases) {
        console.log(`  ${d.name} (${d.sizeOnDisk} bytes)`);
        const db = client.db(d.name);
        const collections = await db.listCollections().toArray();
        for (const c of collections) {
            const count = await db.collection(c.name).countDocuments({});
            console.log(`    -> ${c.name} (${count} docs)`);
        }
    }

    await client.close();
}
main().catch(console.error);
