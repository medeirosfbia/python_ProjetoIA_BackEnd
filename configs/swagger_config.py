swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "AprovIA API - Assistente de Matemática e Inglês",
        "description": "API completa para assistente de matemática  e inglês com chat streaming, e histórico de conversas",
        "version": "2.0.0",
        "contact": {
            "name": "Support Team",
            "email": "support@aprovia.com"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "host": "localhost:5000",
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json", "text/plain"],
    "tags": [
        {
            "name": "chats",
            "description": "Operações relacionadas aos chats"
        },
    ],
    "securityDefinitions": {
        "UserAuth": {
            "type": "apiKey",
            "name": "user_id",
            "in": "query",
            "description": "ID único do usuário para identificação"
        }
    },
    "definitions": {
        "ChatMessage": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["user", "assistant"],
                    "description": "Papel da mensagem no chat"
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo da mensagem"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Data e hora da mensagem"
                }
            },
            "required": ["role", "content"]
        },
        "Chat": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "ID único do chat"
                },
                "title": {
                    "type": "string",
                    "description": "Título do chat baseado na primeira mensagem"
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Data de criação do chat"
                },
                "updated_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Data da última atualização"
                },
                "messages": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/ChatMessage"},
                    "description": "Lista de mensagens do chat"
                }
            },
            "required": ["chat_id", "title"]
        },
        "NewChatRequest": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": ["qwen2-math", "llama3"],
                    "example": "qwen2-math",
                    "description": "Modelo de IA a ser usado (math para matemática, english para inglês)"
                },
                "message": {
                    "type": "string",
                    "example": "Como resolver uma equação de segundo grau?",
                    "description": "Mensagem inicial do usuário"
                }
            },
            "required": ["model", "message"]
        },
        "ContinueChatRequest": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "enum": ["qwen2-math", "llama3"],
                    "example": "qwen2-math",
                    "description": "Modelo de IA a ser usado"
                },
                "message": {
                    "type": "string",
                    "example": "Pode dar um exemplo prático?",
                    "description": "Nova mensagem para continuar a conversa"
                }
            },
            "required": ["model", "message"]
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "string",
                    "description": "Descrição do erro ocorrido"
                }
            },
            "required": ["error"]
        },
        "SuccessResponse": {
            "type": "object",
            "properties": {
                "success": {
                    "type": "string",
                    "description": "Mensagem de sucesso"
                }
            },
            "required": ["success"]
        }
    },
    "paths": {
        "/chats/new": {
            "post": {
                "tags": ["chats"],
                "summary": "Criar um novo chat",
                "description": "Inicia uma nova conversa com o assistente de IA. Retorna resposta em streaming.",
                "security": [{"UserAuth": []}],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "query",
                        "type": "string",
                        "required": True,
                        "description": "ID único do usuário"
                    },
                    {
                        "in": "body",
                        "name": "body",
                        "required": True,
                        "schema": {"$ref": "#/definitions/NewChatRequest"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Chat criado com sucesso. Resposta em streaming.",
                        "headers": {
                            "X-Chat-ID": {
                                "type": "string",
                                "description": "ID do chat criado"
                            }
                        },
                        "schema": {
                            "type": "string",
                            "description": "Resposta do assistente em texto streaming"
                        }
                    },
                    "400": {
                        "description": "Erro de validação",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    }
                },
                "produces": ["text/plain"]
            }
        },
        "/chats/{chat_id}/add": {
            "post": {
                "tags": ["chats"],
                "summary": "Adicionar mensagem a um chat existente",
                "description": "Continua uma conversa existente. Retorna resposta em streaming.",
                "security": [{"UserAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": True,
                        "description": "ID único do usuário"
                    },
                    {
                        "name": "chat_id", 
                        "in": "path", 
                        "type": "string", 
                        "required": True,
                        "description": "ID do chat existente"
                    },
                    {
                        "in": "body",
                        "name": "body",
                        "required": True,
                        "schema": {"$ref": "#/definitions/ContinueChatRequest"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Mensagem adicionada com sucesso. Resposta em streaming.",
                        "headers": {
                            "X-Chat-ID": {
                                "type": "string",
                                "description": "ID do chat"
                            }
                        },
                        "schema": {
                            "type": "string",
                            "description": "Resposta do assistente em texto streaming"
                        }
                    },
                    "400": {
                        "description": "Erro de validação",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    },
                    "404": {
                        "description": "Chat não encontrado",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    }
                },
                "produces": ["text/plain"]
            }
        },
        "/chats": {
            "get": {
                "tags": ["chats"],
                "summary": "Listar chats de um usuário",
                "description": "Retorna a lista de todos os chats do usuário ordenados por data de atualização.",
                "security": [{"UserAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": True,
                        "description": "ID único do usuário"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de chats do usuário",
                        "schema": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "chat_id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "created_at": {"type": "string", "format": "date-time"},
                                    "updated_at": {"type": "string", "format": "date-time"},
                                    "message_count": {"type": "integer"}
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Parâmetro user_id obrigatório",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    }
                }
            }
        },
        "/chats/{chat_id}": {
            "get": {
                "tags": ["chats"],
                "summary": "Obter detalhes de um chat específico",
                "description": "Retorna o histórico completo de mensagens de um chat.",
                "security": [{"UserAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": True,
                        "description": "ID único do usuário"
                    },
                    {
                        "name": "chat_id", 
                        "in": "path", 
                        "type": "string", 
                        "required": True,
                        "description": "ID do chat a ser recuperado"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Detalhes completos do chat",
                        "schema": {"$ref": "#/definitions/Chat"}
                    },
                    "400": {
                        "description": "Parâmetro user_id obrigatório",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    },
                    "404": {
                        "description": "Chat não encontrado",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    }
                }
            }
        },
        "/chats/{chat_id}/delete": {
            "delete": {
                "tags": ["chats"],
                "summary": "Deletar um chat",
                "description": "Remove permanentemente um chat e todo seu histórico de mensagens.",
                "security": [{"UserAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": True,
                        "description": "ID único do usuário"
                    },
                    {
                        "name": "chat_id", 
                        "in": "path", 
                        "type": "string", 
                        "required": True,
                        "description": "ID do chat a ser deletado"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Chat deletado com sucesso",
                        "schema": {"$ref": "#/definitions/SuccessResponse"}
                    },
                    "400": {
                        "description": "Parâmetro user_id obrigatório",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    },
                    "404": {
                        "description": "Chat não encontrado",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    },
                    "500": {
                        "description": "Erro interno do servidor",
                        "schema": {"$ref": "#/definitions/ErrorResponse"}
                    }
                }
            }
        }
    }
}

# Configuração adicional do Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/"
}