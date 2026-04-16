const { MongoClient } = require('mongodb');

async function main() {
    const mongoUri = "mongodb://127.0.0.1:27017";
    console.log("Testing full config:");
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
        await client.connect();
        console.log("Connected successfully to server with FULL config");
        await client.close();
    } catch (err) {
        console.error("Connection failed:", err);
    }
}
main();
