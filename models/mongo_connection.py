import os
from pymongo import MongoClient, ASCENDING, DESCENDING

URL_CONNECTION_MONGODB = os.getenv('URL_CONNECTION_MONGODB')
DATABASE_NAME = os.getenv('DATABASE_NAME')
ASSISTANT_COLLECTION = os.getenv('ASSISTANT_COLLECTION')
EXAMS_COLLECTION = os.getenv('EXAMS_COLLECTION', 'exams')
EXAM_ANSWERS_COLLECTION = os.getenv('EXAM_ANSWERS_COLLECTION', 'exam_answers')
PUSH_TOKENS_COLLECTION = os.getenv('PUSH_TOKENS_COLLECTION', 'push_tokens')
USER_ACTIVITY_COLLECTION = os.getenv('USER_ACTIVITY_COLLECTION', 'user_activity')
USER_ACTIVITY_DAYS_COLLECTION = os.getenv('USER_ACTIVITY_DAYS_COLLECTION', 'user_activity_days')

client = MongoClient(URL_CONNECTION_MONGODB)
db = client[DATABASE_NAME]
collection = db[ASSISTANT_COLLECTION]
exams_collection = db[EXAMS_COLLECTION]
exam_answers_collection = db[EXAM_ANSWERS_COLLECTION]
push_tokens_collection = db[PUSH_TOKENS_COLLECTION]
user_activity_collection = db[USER_ACTIVITY_COLLECTION]
user_activity_days_collection = db[USER_ACTIVITY_DAYS_COLLECTION]

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

# Um aparelho (token) pertence a um único usuário por vez
push_tokens_collection.create_index([
    ("token", ASCENDING)
], unique=True, name="push_token_unique")

push_tokens_collection.create_index([
    ("user_id", ASCENDING)
], name="push_token_user")

# Um documento por usuário com o último dia em que ele usou o app
user_activity_collection.create_index([
    ("user_id", ASCENDING)
], unique=True, name="user_activity_unique")

# Histórico: um documento por usuário por dia de uso (constância no dashboard)
user_activity_days_collection.create_index([
    ("user_id", ASCENDING),
    ("day", DESCENDING)
], unique=True, name="user_activity_day_unique")
