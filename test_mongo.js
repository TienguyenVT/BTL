const { MongoClient } = require('mongodb');

async function main() {
    const mongoUri = "mongodb://127.0.0.1:27017";
    console.log("Testing connection string: " + mongoUri);
    try {
        const client = new MongoClient(mongoUri, {
            authMechanism: "DEFAULT"
        });
        await client.connect();
        console.log("Connected successfully to server");
        await client.close();
    } catch (err) {
        console.error("Connection failed with authMechanism=DEFAULT:", err);
    }
    
    try {
        const client2 = new MongoClient(mongoUri);
        await client2.connect();
        console.log("Connected successfully to server without auth options");
        await client2.close();
    } catch (err) {
        console.error("Connection failed without auth options:", err);
    }
}
main();
