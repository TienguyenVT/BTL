from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv('.env')

client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'), serverSelectionTimeoutMS=5000)
db = client[os.getenv('MONGO_DB_NAME', 'iomt_health_monitor')]

print('Collections:')
for c in db.list_collection_names():
    count = db[c].count_documents({})
    sample = db[c].find_one({}, {'_id': 0})
    fields = list(sample.keys()) if sample else 'empty'
    print('  %s: %d docs | fields: %s' % (c, count, fields))
