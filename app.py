import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, json
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from datetime import datetime

load_dotenv()
# Controllers import
from controllers.embed_controller import embed_file
from controllers.chat_controller import (
    query_old_controller,
    new_chat_controller,
    continue_chat_controller,
    list_chats_controller,
    get_chat_controller,
    delete_chat_controller
)


TEMP_FOLDER = os.getenv('TEMP_FOLDER')
os.makedirs(TEMP_FOLDER, exist_ok=True)



app = Flask(__name__)
CORS(app)
api = Api(app, version='1.0', title='Math Assistant API',
           description='API for Math Assistant')

chat_ns = Namespace('chats', description='Operações de chat')

new_chat_model = chat_ns.model('NewChat', {
    'message': fields.String(required=True, description='Mensagem inicial do usuário')
})

continue_chat_model = chat_ns.model('ContinueChat', {
    'message': fields.String(required=True, description='Mensagem para continuar o chat')
})

@chat_ns.route('/new')
class NewChat(Resource):
    @chat_ns.expect(new_chat_model, validate=True)
    @chat_ns.doc(params={'user_id': 'ID do usuário'})
    def post(self):
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "Parâmetro 'user_id' é obrigatório"}, 400
        data = request.get_json()
        response = new_chat_controller(user_id, data.get('message'))
        if response:
            return {"answer": response}, 200
        else:
            return {"error": "Something went wrong"}, 400

@chat_ns.route('/<string:chat_id>/add')
class ResumeChat(Resource):
    @chat_ns.expect(continue_chat_model, validate=True)
    @chat_ns.doc(params={'user_id': 'ID do usuário'})
    def post(self, chat_id):
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "Parâmetro 'user_id' é obrigatório"}, 400
        data = request.get_json()
        message = data.get('message')
        response = continue_chat_controller(user_id, chat_id, message)
        if response:
            return {"answer": response}, 200
        else:
            return {"error": "Something went wrong"}, 400

def serialize_chat(chat):

    if isinstance(chat, dict):
        for k, v in chat.items():
            if isinstance(v, datetime):
                chat[k] = v.isoformat()
            elif isinstance(v, list):
                chat[k] = [serialize_chat(item) for item in v]
            elif isinstance(v, dict):
                chat[k] = serialize_chat(v)
    return chat

@chat_ns.route('/')
class ListChats(Resource):
    @chat_ns.doc(params={'user_id': 'ID do usuário'})
    def get(self):
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "Parâmetro 'user_id' é obrigatório"}, 400
        chats = list_chats_controller(user_id)
        return [serialize_chat(chat) for chat in chats], 200

@chat_ns.route('/<string:chat_id>')
class GetChat(Resource):
    @chat_ns.doc(params={'user_id': 'ID do usuário'})
    def get(self, chat_id):
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "Parâmetro 'user_id' é obrigatório"}, 400
        chat = get_chat_controller(user_id, chat_id)
        if not chat:
            return {"error": "Conversa não encontrada"}, 404
        return serialize_chat(chat), 200

@chat_ns.route('/<string:chat_id>/delete')
class DeleteChat(Resource):
    @chat_ns.doc(params={'user_id': 'ID do usuário'})
    def delete(self, chat_id):
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "Parâmetro 'user_id' é obrigatório"}, 400
        result = delete_chat_controller(user_id, chat_id)
        if result:
            return {"success": "Conversa deletada com sucesso"}, 200
        else:
            return {"error": "Erro ao deletar conversa"}, 500

api.add_namespace(chat_ns)

if __name__ == "__main__":
    app.run()
