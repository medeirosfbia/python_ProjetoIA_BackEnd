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
    # Sem "host": o Swagger usa o endereço em que a página foi aberta (evita bloqueio de CORS)
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
        {
            "name": "materials",
            "description": "Materiais das matérias no Azure Blob, uma pasta por conteúdo (leitura: todos; escrita: somente admins)"
        },
        {
            "name": "dashboard",
            "description": "Desempenho do usuário: onde estava, onde está, tendência e o que fazer para chegar à meta (padrão 70%). Percentuais de 0 a 100, só sobre questões já corrigidas."
        },
        {
            "name": "notifications",
            "description": "Notificações push (entregues pela Azure Function em consumers_messaging). Também são enviadas automaticamente quando uma prova passa a APROVADO (data.type = exam_published, data.examId) e quando um material é enviado (data.type = material_created, data.conteudo, data.nome). Lembrete diário (data.type = daily_reminder) às 15h para quem ainda não usou o app no dia; qualquer requisição autenticada conta como uso."
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
                "model": {
                    "type": "string",
                    "enum": ["qwen2-math", "llama3"],
                    "description": "Alias público do tutor persistido no chat"
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
            "required": ["message"]
        },
        "ChatModelRequest": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "enum": ["qwen2-math", "llama3"]}
            },
            "required": ["model"]
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "string",
                    "description": "Descrição do erro ocorrido"
                },
                "code": {
                    "type": "string",
                    "description": "Código estruturado, quando aplicável"
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
                "topico": {
                    "type": "string",
                    "maxLength": 80,
                    "example": "Equações do 1º grau",
                    "description": "Opcional. Assunto dentro da matéria, usado no dashboard para apontar os pontos fracos"
                },
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
        "Material": {
            "type": "object",
            "properties": {
                "conteudo": {"type": "string", "example": "matematica"},
                "nome": {"type": "string", "example": "equacoes_1o_grau.pdf"},
                "caminho": {"type": "string", "example": "matematica/equacoes_1o_grau.pdf"},
                "tamanho_bytes": {"type": "integer", "example": 182044},
                "content_type": {"type": "string", "example": "application/pdf"},
                "atualizado_em": {"type": "string", "format": "date-time"},
                "metadata": {
                    "type": "object",
                    "description": "enviado_por, enviado_em, atualizado_por, atualizado_em"
                }
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
        },
        "DashboardTrend": {
            "type": "object",
            "description": "Regressão linear das últimas 10 tentativas; null com menos de 3",
            "properties": {
                "direcao": {"type": "string", "enum": ["subindo", "estavel", "caindo"]},
                "pp_por_tentativa": {"type": "number", "example": 2.1, "description": "Pontos percentuais ganhos (ou perdidos) por tentativa"}
            }
        },
        "DashboardSummary": {
            "type": "object",
            "properties": {
                "tentativas": {"type": "integer", "example": 12},
                "inicio": {"type": "number", "example": 48.0, "description": "Média das 3 primeiras tentativas"},
                "anterior": {"type": "number", "example": 55.0, "description": "Média das 5 tentativas antes das últimas 5 (null se não houver)"},
                "atual": {"type": "number", "example": 63.0, "description": "Média das últimas 5 tentativas"},
                "variacao": {"type": "number", "example": 8.0, "description": "atual - anterior"},
                "tendencia": {"$ref": "#/definitions/DashboardTrend"},
                "gap": {"type": "number", "example": 7.0, "description": "Quanto falta para a meta (0 se já atingiu)"},
                "projecao_tentativas_ate_meta": {"type": "integer", "example": 4, "description": "0 se já atingiu; null se a tendência não é positiva ou passa de 50"}
            }
        },
        "DashboardSubject": {
            "type": "object",
            "description": "DashboardSummary da matéria, mais pontos fracos e ações",
            "properties": {
                "assunto": {"type": "string", "example": "Matemática"},
                "tentativas": {"type": "integer"},
                "inicio": {"type": "number"},
                "anterior": {"type": "number"},
                "atual": {"type": "number"},
                "variacao": {"type": "number"},
                "tendencia": {"$ref": "#/definitions/DashboardTrend"},
                "gap": {"type": "number"},
                "projecao_tentativas_ate_meta": {"type": "integer"},
                "topicos_fracos": {
                    "type": "array",
                    "description": "Tópicos abaixo da meta (mín. 3 questões, últimas 20), do pior para o melhor",
                    "items": {"type": "object", "properties": {
                        "topico": {"type": "string", "example": "Porcentagem"},
                        "percentual": {"type": "number", "example": 40.0},
                        "questoes": {"type": "integer", "example": 5}
                    }}
                },
                "acoes": {
                    "type": "object",
                    "description": "Só para matérias abaixo da meta (null nas demais). Até 5 itens por lista.",
                    "properties": {
                        "provas_nao_feitas": {"type": "array", "items": {"type": "object", "properties": {
                            "prova_id": {"type": "string"}, "titulo": {"type": "string"}}}},
                        "refazer": {"type": "array", "description": "Provas publicadas que permitem refazer, com a última tentativa abaixo da meta",
                                    "items": {"type": "object", "properties": {
                            "prova_id": {"type": "string"}, "titulo": {"type": "string"}, "percentual": {"type": "number"}}}},
                        "questoes_erradas": {"type": "array", "description": "Erradas ou em branco na última tentativa de cada prova",
                                             "items": {"type": "object", "properties": {
                            "prova_id": {"type": "string"}, "titulo_prova": {"type": "string"}, "id_questao": {"type": "string"},
                            "topico": {"type": "string"}, "explicacao_gabarito": {"type": "string"}}}},
                        "pasta_materiais": {"type": "string", "example": "matematica", "description": "Pasta em /materials para a matéria (pode não existir)"}
                    }
                }
            }
        },
        "DashboardResponse": {
            "type": "object",
            "properties": {
                "meta_percentual": {"type": "number", "example": 70},
                "geral": {
                    "description": "DashboardSummary de todas as tentativas, mais a evolução",
                    "allOf": [
                        {"$ref": "#/definitions/DashboardSummary"},
                        {"type": "object", "properties": {"evolucao": {
                            "type": "array",
                            "description": "Últimas 50 tentativas em ordem cronológica (para o gráfico)",
                            "items": {"type": "object", "properties": {
                                "data": {"type": "string", "format": "date-time"},
                                "percentual": {"type": "number", "example": 45.0},
                                "assunto": {"type": "string"},
                                "prova_id": {"type": "string"},
                                "titulo_prova": {"type": "string"}
                            }}
                        }}}
                    ]
                },
                "por_materia": {"type": "array", "description": "Ordenado do maior gap para o menor", "items": {"$ref": "#/definitions/DashboardSubject"}},
                "dados_insuficientes": {"type": "array", "items": {"type": "string"}, "description": "Matérias com menos de 3 tentativas (sem tendência)"},
                "materias_nao_iniciadas": {"type": "array", "items": {"type": "string"}, "description": "Matérias com provas publicadas que o usuário nunca fez"},
                "aguardando_correcao": {"type": "integer", "description": "Tentativas que só têm questões pendentes de correção (fora dos cálculos)"},
                "constancia": {"type": "object", "properties": {
                    "dias_seguidos": {"type": "integer", "example": 4, "description": "Sequência terminando hoje ou ontem (máx. 90)"},
                    "dias_ultimos_7": {"type": "integer", "example": 5},
                    "dias_ultimos_30": {"type": "integer", "example": 18}
                }}
            }
        },
        "PushTokenRequest": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "example": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
                    "description": "ExpoPushToken gerado pelo app (prefixo ExponentPushToken[ ou ExpoPushToken[)"
                },
                "platform": {"type": "string", "enum": ["android", "ios"], "example": "android"}
            },
            "required": ["token", "platform"]
        },
        "PushTokenDeleteRequest": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "example": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"}
            },
            "required": ["token"]
        },
        "NotificationSendRequest": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "maxLength": 100, "example": "Aviso"},
                "body": {"type": "string", "maxLength": 500, "example": "Amanhã tem simulado!"},
                "recipients": {
                    "description": "\"all\" (padrão) ou lista de 1 a 500 usuários (sub do JWT); repetidos são ignorados",
                    "example": ["ana", "bruno"]
                },
                "data": {
                    "type": "object",
                    "description": "Dados extras repassados ao app; a Function adiciona data.type = \"custom\"",
                    "example": {"examId": "prova_abc123"}
                }
            },
            "required": ["title", "body"]
        },
        "NotificationQueuedResponse": {
            "type": "object",
            "properties": {
                "messageId": {"type": "string", "description": "Id da mensagem na fila aprovia-notifications"}
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
                    },
                    "409": {
                        "description": "Chat sem modelo ou modelo divergente",
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
        "/chats/{chat_id}/model": {
            "patch": {
                "tags": ["chats"],
                "summary": "Associar tutor a um chat legado",
                "description": "Disponível apenas para o dono autenticado. Só define model quando o campo está ausente ou null; repetir o mesmo model é seguro. Não altera mensagens.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "chat_id", "in": "path", "type": "string", "required": True},
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/ChatModelRequest"}}
                ],
                "responses": {
                    "200": {"description": "Tutor persistido", "schema": {"type": "object", "properties": {"chat_id": {"type": "string"}, "model": {"type": "string"}}}},
                    "400": {"description": "Modelo inválido", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "404": {"description": "Chat não encontrado", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "409": {"description": "Chat já associado a outro tutor", "schema": {"$ref": "#/definitions/ErrorResponse"}}
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
        "/materials/folders": {
            "get": {
                "tags": ["materials"],
                "summary": "Listar pastas (conteúdos)",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "Nomes das pastas", "schema": {"type": "array", "items": {"type": "string"}, "example": ["ingles", "matematica"]}},
                    "503": {"description": "Armazenamento não configurado", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            }
        },
        "/materials": {
            "get": {
                "tags": ["materials"],
                "summary": "Listar materiais",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "conteudo", "in": "query", "type": "string", "required": False,
                     "description": "Filtra por pasta. 'Matemática Básica' é normalizado para 'matematica-basica'"}
                ],
                "responses": {
                    "200": {"description": "Materiais", "schema": {"type": "array", "items": {"$ref": "#/definitions/Material"}}},
                    "400": {"description": "Conteúdo inválido", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}}
                }
            }
        },
        "/materials/{conteudo}": {
            "post": {
                "tags": ["materials"],
                "summary": "Enviar material (admin)",
                "description": (
                    "Grava o arquivo em <conteudo>/<nome do arquivo>; a pasta é criada automaticamente. "
                    "Extensões aceitas: pdf, txt, md, csv, doc, docx, ppt, pptx, xls, xlsx, png, jpg, jpeg."
                ),
                "security": [{"BearerAuth": []}],
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {"name": "conteudo", "in": "path", "type": "string", "required": True, "description": "Pasta, ex.: matematica"},
                    {"name": "arquivo", "in": "formData", "type": "file", "required": True}
                ],
                "responses": {
                    "201": {"description": "Material criado", "schema": {"$ref": "#/definitions/Material"}},
                    "400": {"description": "Arquivo inválido", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "409": {"description": "Já existe um arquivo com esse nome na pasta", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "413": {"description": "Arquivo acima do limite", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            }
        },
        "/materials/{conteudo}/{nome}": {
            "get": {
                "tags": ["materials"],
                "summary": "Obter dados do material",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "conteudo", "in": "path", "type": "string", "required": True},
                    {"name": "nome", "in": "path", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Material", "schema": {"$ref": "#/definitions/Material"}},
                    "404": {"description": "Material não encontrado", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            },
            "put": {
                "tags": ["materials"],
                "summary": "Substituir arquivo do material (admin)",
                "description": "O novo arquivo precisa ter a mesma extensão; o nome e a pasta continuam os mesmos.",
                "security": [{"BearerAuth": []}],
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {"name": "conteudo", "in": "path", "type": "string", "required": True},
                    {"name": "nome", "in": "path", "type": "string", "required": True},
                    {"name": "arquivo", "in": "formData", "type": "file", "required": True}
                ],
                "responses": {
                    "200": {"description": "Material atualizado", "schema": {"$ref": "#/definitions/Material"}},
                    "400": {"description": "Arquivo inválido", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "404": {"description": "Material não encontrado", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            },
            "delete": {
                "tags": ["materials"],
                "summary": "Deletar material (admin)",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "conteudo", "in": "path", "type": "string", "required": True},
                    {"name": "nome", "in": "path", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Material deletado", "schema": {"$ref": "#/definitions/SuccessResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "404": {"description": "Material não encontrado", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            }
        },
        "/materials/{conteudo}/{nome}/download": {
            "get": {
                "tags": ["materials"],
                "summary": "Baixar/visualizar o arquivo",
                "description": "Retorna o arquivo em streaming, inline por padrão; use download=1 para forçar o download.",
                "security": [{"BearerAuth": []}],
                "produces": ["application/octet-stream"],
                "parameters": [
                    {"name": "conteudo", "in": "path", "type": "string", "required": True},
                    {"name": "nome", "in": "path", "type": "string", "required": True},
                    {"name": "download", "in": "query", "type": "string", "enum": ["1"], "required": False}
                ],
                "responses": {
                    "200": {"description": "Conteúdo do arquivo", "schema": {"type": "file"}},
                    "404": {"description": "Material não encontrado", "schema": {"$ref": "#/definitions/ErrorResponse"}}
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
        },
        "/dashboard/me": {
            "get": {
                "tags": ["dashboard"],
                "summary": "Dashboard de desempenho do usuário",
                "description": "Calculado na hora a partir das tentativas em provas e dos dias de uso. Dissertativas pendentes ficam fora até serem corrigidas.",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "Dashboard", "schema": {"$ref": "#/definitions/DashboardResponse"}}
                }
            }
        },
        "/notifications/tokens": {
            "post": {
                "tags": ["notifications"],
                "summary": "Cadastrar aparelho",
                "description": "Chamado pelo app após o login e ao restaurar a sessão. Associa o token ao usuário do JWT; repetir não duplica. Se o token já pertencia a outro usuário (troca de conta no aparelho), passa a ser do atual.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/PushTokenRequest"}}
                ],
                "responses": {
                    "201": {"description": "Token cadastrado", "schema": {"$ref": "#/definitions/PushTokenRequest"}},
                    "400": {"description": "Dados inválidos", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}}
                }
            },
            "delete": {
                "tags": ["notifications"],
                "summary": "Remover aparelho",
                "description": "Chamado pelo app no logout e ao excluir a conta, antes de descartar o JWT. Só remove tokens do próprio usuário.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/PushTokenDeleteRequest"}}
                ],
                "responses": {
                    "200": {"description": "Token removido", "schema": {"$ref": "#/definitions/SuccessResponse"}},
                    "400": {"description": "Dados inválidos", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "404": {"description": "Token não pertence ao usuário", "schema": {"$ref": "#/definitions/ErrorResponse"}}
                }
            }
        },
        "/notifications/send": {
            "post": {
                "tags": ["notifications"],
                "summary": "Enviar notificação avulsa (admin)",
                "description": "Publica na fila de notificações; a Azure Function entrega via Expo Push. O 202 indica que a notificação foi enfileirada, não que chegou ao aparelho.",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/NotificationSendRequest"}}
                ],
                "responses": {
                    "202": {"description": "Notificação enfileirada", "schema": {"$ref": "#/definitions/NotificationQueuedResponse"}},
                    "400": {"description": "Dados inválidos", "schema": {"$ref": "#/definitions/ValidationErrorResponse"}},
                    "403": {"description": "Usuário não é admin", "schema": {"$ref": "#/definitions/ErrorResponse"}},
                    "503": {"description": "Fila indisponível", "schema": {"$ref": "#/definitions/ErrorResponse"}}
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
