import os
from pymongo import MongoClient, ASCENDING, DESCENDING

URL_CONNECTION_MONGODB = os.getenv('URL_CONNECTION_MONGODB')
DATABASE_NAME = os.getenv('DATABASE_NAME')
ASSISTANT_COLLECTION = os.getenv('ASSISTANT_COLLECTION')

client = MongoClient(URL_CONNECTION_MONGODB)
db = client[DATABASE_NAME]  
collection = db[ASSISTANT_COLLECTION]

collection.create_index([
    ("user_id", ASCENDING),
    ("chat_id", ASCENDING)
], unique=True, name="user_chat_unique")

collection.create_index([
    ("user_id", ASCENDING),
    ("updated_at", DESCENDING)
], name="user_recent_chats")
