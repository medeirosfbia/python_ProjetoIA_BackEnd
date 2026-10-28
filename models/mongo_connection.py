import os
from pymongo import MongoClient, ASCENDING, DESCENDING

URL_CONNECTION_MONGODB = os.getenv('URL_CONNECTION_MONGODB')
DATABASE_NAME = os.getenv('DATABASE_NAME')
ASSISTANT_COLLECTION = os.getenv('ASSISTANT_COLLECTION')
EXAMS_COLLECTION = os.getenv('EXAMS_COLLECTION', 'exams')
EXAM_ANSWERS_COLLECTION = os.getenv('EXAM_ANSWERS_COLLECTION', 'exam_answers')

client = MongoClient(URL_CONNECTION_MONGODB)
db = client[DATABASE_NAME]
collection = db[ASSISTANT_COLLECTION]
exams_collection = db[EXAMS_COLLECTION]
exam_answers_collection = db[EXAM_ANSWERS_COLLECTION]

collection.create_index([
    ("user_id", ASCENDING),
    ("chat_id", ASCENDING)
], unique=True, name="user_chat_unique")

collection.create_index([
    ("user_id", ASCENDING),
    ("updated_at", DESCENDING)
], name="user_recent_chats")

exams_collection.create_index([
    ("status", ASCENDING),
    ("contexto.assunto_materia", ASCENDING)
], name="exam_status_subject")

# Impede que duas submissões simultâneas gravem o mesmo número de tentativa
exam_answers_collection.create_index([
    ("prova_id", ASCENDING),
    ("usuario_id", ASCENDING),
    ("tentativa", ASCENDING)
], unique=True, name="exam_user_attempt_unique")

exam_answers_collection.create_index([
    ("usuario_id", ASCENDING),
    ("enviado_em", DESCENDING)
], name="user_recent_answers")
