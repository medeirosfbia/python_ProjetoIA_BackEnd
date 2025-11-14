import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

class TestListChats:
    def test_list_chats_without_user_id(self, client):
        """Testa se retorna erro quando user_id não é informado"""
        response = client.get('/chats')
        assert response.status_code == 400
        
    @patch('app.list_chats_controller')  # Mude para onde é importado no app.py
    def test_list_chats_with_user_id(self, mock_list_chats, client):
        """Testa se retorna lista de chats com user_id válido"""
        mock_list_chats.return_value = [
            {
                "chat_id": "chat_123",
                "user_id": "medeirosfbia",
                "title": "Chat 1",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        
        response = client.get('/chats?user_id=medeirosfbia')
        assert response.status_code == 200
        assert isinstance(response.json, list)
        mock_list_chats.assert_called_once()

class TestGetChat:
    def test_get_chat_without_user_id(self, client):
        """Testa se retorna erro quando user_id não é informado"""
        response = client.get('/chats/123')
        assert response.status_code == 400
        
    @patch('app.get_chat_controller')  # Mude para onde é importado
    def test_get_chat_success(self, mock_get_chat, client):
        """Testa retorno bem-sucedido de um chat"""
        mock_get_chat.return_value = {
            "chat_id": "chat_123",
            "user_id": "medeirosfbia",
            "title": "Chat Test",
            "messages": [
                {"role": "user", "content": "Olá"},
                {"role": "assistant", "content": "Oi!"}
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = client.get('/chats/chat_123?user_id=medeirosfbia')
        assert response.status_code == 200
        assert response.json["chat_id"] == "chat_123"
        
    @patch('app.get_chat_controller')
    def test_get_chat_not_found(self, mock_get_chat, client):
        """Testa retorno 404 quando chat não existe"""
        mock_get_chat.return_value = None
        
        response = client.get('/chats/invalid_id?user_id=medeirosfbia')
        assert response.status_code == 404

class TestDeleteChat:
    def test_delete_chat_without_user_id(self, client):
        """Testa se retorna erro quando user_id não é informado"""
        response = client.delete('/chats/123/delete')
        assert response.status_code == 400
        
    @patch('app.delete_chat_controller')
    def test_delete_chat_success(self, mock_delete, client):
        """Testa exclusão bem-sucedida"""
        mock_delete.return_value = True
        
        response = client.delete('/chats/chat_123/delete?user_id=medeirosfbia')
        assert response.status_code == 200
        
    @patch('app.delete_chat_controller')
    def test_delete_chat_failure(self, mock_delete, client):
        """Testa erro ao deletar"""
        mock_delete.return_value = False
        
        response = client.delete('/chats/chat_123/delete?user_id=medeirosfbia')
        assert response.status_code == 500

class TestNewChat:
    @patch('app.new_chat_controller')
    def test_new_chat_success(self, mock_new_chat, client):
        """Testa criação bem-sucedida de novo chat"""
        mock_new_chat.return_value = {
            'chat_id': 'new_chat_123',
            'resposta_stream': iter([b'Resposta ', b'do ', b'modelo'])
        }
        
        response = client.post(
            '/chats/new?user_id=medeirosfbia',
            json={'model': 'math', 'message': '2 + 2 = ?'}
        )
        assert response.status_code == 200
        
    def test_new_chat_without_user_id(self, client):
        """Testa erro quando user_id não é fornecido"""
        response = client.post(
            '/chats/new',
            json={'model': 'math', 'message': '2 + 2 = ?'}
        )
        assert response.status_code == 400

class TestContinueChat:
    @patch('app.continue_chat_controller')
    def test_continue_chat_success(self, mock_continue, client):
        """Testa continuação bem-sucedida de chat"""
        mock_continue.return_value = {
            'chat_id': 'chat_123',
            'resposta_stream': iter([b'Continuando...'])
        }
        
        response = client.post(
            '/chats/chat_123/add?user_id=medeirosfbia',
            json={'model': 'math', 'message': 'E 3 + 3?'}
        )
        assert response.status_code == 200