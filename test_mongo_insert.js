const { MongoClient } = require('mongodb');

async function main() {
    const mongoUri = "mongodb://127.0.0.1:27017";
    console.log("Testing insert operation with FULL config:");
    try {
        const client = new MongoClient(mongoUri, {
            appName: "nodered-test",
            auth: null, // Because node.credentials.username and password are not set
            authMechanism: "DEFAULT",
            authSource: undefined,
            tls: false,
            tlsCAFile: undefined,
            tlsCertificateKeyFile: undefined,
            tlsInsecure: false,
            connectTimeoutMS: 30000,
            socketTimeoutMS: 0,
            minPoolSize: 0,
            maxPoolSize: 100,
            maxIdleTimeMS: 0
        });
        const db = client.db("iomt_health_monitor");
        await db.collection("test_conn").insertOne({ test: 1 });
        console.log("Inserted successfully");
        await client.close();
    } catch (err) {
        console.error("Operation failed:", err);
    }
}
main();
