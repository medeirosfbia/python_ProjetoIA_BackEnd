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
        {
            "name": "exams",
            "description": "Provas/testes (criar, editar e deletar: somente admins) e respostas dos usuários"
        },
    ],
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Informe o token no formato: Bearer <JWT>"
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
        },
        "ValidationErrorResponse": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Dados inválidos"},
                "detalhes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["titulo é obrigatório"]
                }
            }
        },
        "ExamQuestion": {
            "type": "object",
            "description": (
                "Questão polimórfica. multipla_escolha usa opcoes/resposta_correta_id/explicacao_gabarito; "
                "dissertativa usa chave_correcao/limite_caracteres; desafio_codigo usa "
                "linguagem_permitida/codigo_inicial/casos_de_teste. Os campos de gabarito "
                "não são retornados para usuários comuns."
            ),
            "properties": {
                "id_questao": {"type": "string", "example": "q1"},
                "ordem": {"type": "integer", "example": 1},
                "tipo": {"type": "string", "enum": ["multipla_escolha", "dissertativa", "desafio_codigo"]},
                "peso": {"type": "number", "example": 2.0},
                "enunciado": {"type": "string", "example": "Qual é o valor de x na equação 2x + 6 = 14?"},
                "opcoes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}, "texto": {"type": "string"}}
                    },
                    "example": [{"id": "op_a", "texto": "x = 3"}, {"id": "op_b", "texto": "x = 4"}]
                },
                "resposta_correta_id": {"type": "string", "example": "op_b"},
                "explicacao_gabarito": {"type": "string"},
                "chave_correcao": {"type": "string"},
                "limite_caracteres": {"type": "integer"}
            },
            "required": ["id_questao", "tipo", "peso", "enunciado"]
        },
        "ExamRequest": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string", "example": "Simulado de Matemática: Equações e Porcentagem"},
                "status": {
                    "type": "string",
                    "enum": ["RASCUNHO", "APROVADO", "ARQUIVADO"],
                    "default": "RASCUNHO",
                    "description": "Somente provas APROVADO aparecem para usuários comuns"
                },
                "contexto": {
                    "type": "object",
                    "properties": {
                        "assunto_materia": {"type": "string", "example": "Matemática"},
                        "gerado_com_ia": {"type": "object"}
                    },
                    "required": ["assunto_materia"]
                },
                "configuracoes_teste": {
                    "type": "object",
                    "properties": {
                        "tempo_limite_minutos": {"type": "integer", "example": 30},
                        "nota_maxima": {"type": "number", "default": 10.0},
                        "permite_refazer": {"type": "boolean", "default": True}
                    }
                },
                "questoes": {"type": "array", "items": {"$ref": "#/definitions/ExamQuestion"}}
            },
            "required": ["titulo", "contexto", "questoes"]
        },
        "Exam": {
            "type": "object",
            "description": "Prova gravada. contexto também recebe criado_por, data_criacao, atualizado_por e data_atualizacao.",
            "properties": {
                "_id": {"type": "string", "example": "prova_exemplo_matematica_001"},
                "titulo": {"type": "string"},
                "status": {"type": "string"},
                "contexto": {"type": "object"},
                "configuracoes_teste": {"type": "object"},
                "total_questoes": {"type": "integer"},
                "questoes": {"type": "array", "items": {"$ref": "#/definitions/ExamQuestion"}}
            }
        },
        "SubmitAnswersRequest": {
            "type": "object",
            "properties": {
                "respostas": {
                    "type": "array",
                    "description": "Questões não enviadas contam como em branco (0 pontos)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_questao": {"type": "string", "example": "q1"},
                            "resposta": {
                                "type": "string",
                                "example": "op_b",
                                "description": "Id da opção (múltipla escolha) ou texto/código"
                            }
                        },
                        "required": ["id_questao"]
                    }
                },
                "tempo_gasto_segundos": {"type": "integer", "example": 420}
            },
            "required": ["respostas"]
        },
        "ExamAnswer": {
            "type": "object",
            "description": "Tentativa corrigida, guardada para comparação de desempenho",
            "properties": {
                "_id": {"type": "string", "example": "resp_1a2b3c4d5e6f"},
                "prova_id": {"type": "string"},
                "usuario_id": {"type": "string"},
                "tentativa": {"type": "integer", "example": 1},
                "titulo_prova": {"type": "string"},
                "assunto_materia": {"type": "string"},
                "enviado_em": {"type": "string", "format": "date-time"},
                "tempo_gasto_segundos": {"type": "integer"},
                "respostas": {
                    "type": "array",
                    "description": "Por questão: resposta, correta, pontos_obtidos e status_correcao (corrigida, pendente ou em_branco)",
                    "items": {"type": "object"}
                },
                "resultado": {
                    "type": "object",
                    "properties": {
                        "acertos": {"type": "integer"},
                        "total_questoes": {"type": "integer"},
                        "pontos_obtidos": {"type": "number"},
                        "pontos_possiveis": {"type": "number"},
                        "nota_obtida": {"type": "number"},
                        "nota_maxima": {"type": "number"},
                        "questoes_pendentes_correcao": {"type": "integer"},
                        "correcao_concluida": {"type": "boolean"}
                    }
                }
            }
        }
    },
    "paths": {
        "/chats/new": {
            "post": {
                "tags": ["chats"],
                "summary": "Criar um novo chat",
                "description": "Inicia uma nova conversa com o assistente de IA. Retorna resposta em streaming.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "query",
                        "type": "string",
                        "required": False,
                        "description": "Parâmetro legado opcional; deve corresponder ao sub do JWT"
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
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": False,
                        "description": "Parâmetro legado opcional; deve corresponder ao sub do JWT"
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
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": False,
                        "description": "Parâmetro legado opcional; deve corresponder ao sub do JWT"
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
                        "description": "Parâmetro user_id divergente do usuário autenticado",
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
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": False,
                        "description": "Parâmetro legado opcional; deve corresponder ao sub do JWT"
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
                        "description": "Parâmetro user_id divergente do usuário autenticado",
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
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "user_id", 
                        "in": "query", 
                        "type": "string", 
                        "required": False,
                        "description": "Parâmetro legado opcional; deve corresponder ao sub do JWT"
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
                        "description": "Parâmetro user_id divergente do usuário autenticado",
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
        },
        "/exams": {
            "get": {
                "tags": ["exams"],
                "summary": "Listar provas",
                "description": "Resumo das provas, sem as questões. Usuários comuns veem apenas provas APROVADO.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "assunto", "in": "query", "type": "string", "required": False,
                     "description": "Filtra por contexto.assunto_materia"},
                    {"name": "status", "in": "query", "type": "string", "required": False,
                     "enum": ["RASCUNHO", "APROVADO", "ARQUIVADO"],
                     "description": "Filtro de status (somente admins)"}
                ],
                "responses": {
                    "200": {"description": "Lista de provas", "schema": {"type": "array", "items": {"$ref": "#/definitions/Exam"}}}
                }
            },
            "post": {
                "tags": ["exams"],
                "summary": "Criar prova (admin)",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/ExamRequest"}}
                ],
                "responses": {
                    "201": {"description": "Prova criada", "schema": {"$ref": "#/definitions/Exam"}},
                    "400": {"description": "Dados inválidos", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            }
        },
        "/exams/answers": {
            "get": {
                "tags": ["exams"],
                "summary": "Histórico de desempenho do usuário",
                "description": "Resultado de todas as tentativas do usuário autenticado, sem o detalhe por questão.",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "Tentativas (mais recentes primeiro)", "schema": {"type": "array", "items": {"$ref": "#/definitions/ExamAnswer"}}}
                }
            }
        },
        "/exams/{exam_id}": {
            "get": {
                "tags": ["exams"],
                "summary": "Obter prova",
                "description": "Admins recebem a prova completa; usuários comuns recebem a prova sem o gabarito.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "exam_id", "in": "path", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Prova", "schema": {"$ref": "#/definitions/Exam"}},
                    "404": {"description": "Prova não encontrada", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            },
            "put": {
                "tags": ["exams"],
                "summary": "Editar prova (admin)",
                "description": "Substitui a prova inteira. Tentativas já enviadas não mudam, pois guardam uma cópia do gabarito.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "exam_id", "in": "path", "type": "string", "required": True},
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/ExamRequest"}}
                ],
                "responses": {
                    "200": {"description": "Prova atualizada", "schema": {"$ref": "#/definitions/Exam"}},
                    "400": {"description": "Dados inválidos", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "404": {"description": "Prova não encontrada", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            },
            "delete": {
                "tags": ["exams"],
                "summary": "Deletar prova (admin)",
                "description": "Remove a prova. As respostas já enviadas são mantidas para o histórico de desempenho.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "exam_id", "in": "path", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Prova deletada", "schema": {"$ref": "#/definitions/SuccessResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "404": {"description": "Prova não encontrada", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            }
        },
        "/exams/{exam_id}/answers": {
            "post": {
                "tags": ["exams"],
                "summary": "Enviar respostas",
                "description": (
                    "Corrige automaticamente as questões de múltipla escolha e grava a tentativa. "
                    "Dissertativas e desafios de código ficam com status_correcao = pendente."
                ),
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "exam_id", "in": "path", "type": "string", "required": True},
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/SubmitAnswersRequest"}}
                ],
                "responses": {
                    "201": {"description": "Tentativa corrigida e gravada", "schema": {"$ref": "#/definitions/ExamAnswer"}},
                    "400": {"description": "Respostas inválidas", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "404": {"description": "Prova não encontrada", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "409": {"description": "A prova não permite refazer", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            },
            "get": {
                "tags": ["exams"],
                "summary": "Minhas tentativas nesta prova",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "exam_id", "in": "path", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Tentativas com detalhe por questão", "schema": {"type": "array", "items": {"$ref": "#/definitions/ExamAnswer"}}}
                }
            }
        },
        "/exams/{exam_id}/answers/all": {
            "get": {
                "tags": ["exams"],
                "summary": "Todas as tentativas da prova (admin)",
                "description": "Resultado de todos os usuários, para comparação de desempenho.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "exam_id", "in": "path", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Tentativas", "schema": {"type": "array", "items": {"$ref": "#/definitions/ExamAnswer"}}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}}
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