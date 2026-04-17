# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB_NAME")]
coll = db['final_result']
dl = db['datalake_raw']

print("=== Test $in on final_result ===")

# find() with $in
docs_in = list(coll.find({'label': {'$in': ['Stress', 'Fever']}}).limit(3))
print('find with in [Stress,Fever]:', len(docs_in))

# count_documents with $in
cnt_in = coll.count_documents({'label': {'$in': ['Stress', 'Fever']}})
print('count_documents with in [Stress,Fever]:', cnt_in)

# regex workaround
docs_regex = list(coll.find({'label': {'$regex': '^(Stress|Fever)$'}}).limit(3))
print('find with regex:', len(docs_regex))

# Try aggregate on final_result
try:
    result = list(coll.aggregate([{'$match': {'label': {'$in': ['Stress', 'Fever']}}}, {'$count': 'total'}]))
    print('aggregate in on final_result:', result)
except Exception as e:
    print('aggregate error on final_result:', e)

# Check datalake_raw directly
try:
    result2 = list(dl.aggregate([{'$match': {'prediction.label': {'$in': ['Stress', 'Fever']}}}, {'$count': 'total'}]))
    print('aggregate in on datalake_raw:', result2)
except Exception as e:
    print('aggregate error on datalake_raw:', e)

# Check what Spring Data sends - check if it's using Criteria.in() vs $in
# Let's verify by checking the Spring Data MongoDB query builder
# Criteria.in() creates {field: {$in: [...]}}
# Let's see if there's a version mismatch

print()
print("=== PyMongo version ===")
print(pymongo_version := MongoClient().__class__.__module__)
import pymongo
print('pymongo version:', pymongo.version)

# Check MongoDB server version
try:
    result3 = db.command({'buildInfo': 1})
    print('MongoDB server version:', result3.get('version'))
except:
    pass

# Key test: does the view's $match {prediction.label: {$exists True ne None}} affect $in?
# The view pipeline: $match -> $addFields -> $project {_id:0} -> $sort
# When you query the view, MongoDB should merge the query with the $match stage
# BUT: if your query has a field that doesn't exist in the view's projected output,
# MongoDB might fail to merge properly

# Test: what happens if I query for a field that's NOT in the view?
try:
    cnt_test = coll.count_documents({'bogus_field': 'value'})
    print('Query for bogus_field:', cnt_test)
except Exception as e:
    print('bogus_field error:', e)

# The view's $project {_id:0} removes _id
# But the $match stage in the view filters by prediction.label
# When querying the VIEW with label=$in, MongoDB should push the $in into the view's $match
# BUT: the view's $match uses prediction.label, NOT label
# MongoDB can't push down label queries because label doesn't exist until $addFields

print()
print("=== Root cause hypothesis ===")
print("View pipeline: $match(prediction.label exists/ne null) -> $addFields(label:prediction.label) -> $project(_id:0) -> $sort")
print("Query: label in [Stress,Fever]")
print("MongoDB must evaluate: ($match) AND ($addFields AND $project AND query)")
print("The $in query cannot be pushed into the view's $match because label is not yet computed")
print("So MongoDB runs: full view scan -> filter by computed label field")
print("This should work... unless MongoDB has a bug with $in on views with $project {_id:0}")
