# AprovIA — Backend (API)

API backend em Flask para um assistente de Matemática/Inglês com chat em streaming, persistência (MongoDB).
Deployed URL: https://4.206.202.49.nip.io  
Deployment: Aplicação está deployada na Azure usando as etapas/configurações do script de deploy [deploy_aprovia.sh.sh](deploy_aprovia.sh).

## Sumário
- Visão geral
- Arquitetura e pastas
- Tecnologias e dependências
- Configuração (.env)
- Como rodar (desenvolvimento / produção / Docker)
- Endpoints principais
- Swagger / OpenAPI
- Streaming
- Persistência
- Embeddings
- Troubleshooting
- Deployment (Azure)
- Próximos passos

## Visão geral
AprovIA fornece:
- criação/continuação de chats com resposta em streaming (integração com LLM local via Ollama);
- histórico de conversas (MongoDB);

## Estrutura do projeto (resumida)
- `app.py` — ponto de entrada e rotas HTTP
- `configs/` — configurações (ex.: `swagger_config.py`)
- `controllers/` — mapeamento de rotas para serviços
- `services/` — lógica de negócio (`chat_service`, `embed_service`)
- `models/` — persistência e wrapper para vector DB (`mongo_connection`, `history`, `vector_db`)
- `_temp/` — arquivos temporários (definido em `.env`)
- `requirements.txt`, `sampleenv.txt`, `Dockerfile`, `Procfile`, `deploy_aprovia.sh.sh`

Arquivos importantes:
- `app.py` (rotas e inicialização)
- `configs/swagger_config.py` (template Swagger)
- `deploy_aprovia.sh.sh` (script de deploy / configuração do servidor)

## Tecnologias e dependências (resumido)
- Python 3.10+
- Flask, Flask-CORS, Flasgger (Swagger UI)
- Ollama (LLM local + streaming)
- PyMongo (MongoDB) com `certifi` e `dnspython`
- python-dotenv
- gunicorn (produção)
Consulte `requirements.txt` para versões e pacotes.

## Configuração (.env)
Copie `sampleenv.txt` → `.env` e ajuste:
- TEMP_FOLDER, CHROMA_PATH, COLLECTION_NAME
- LLM_MODEL
- URL_CONNECTION_MONGODB
- DATABASE_NAME, ASSISTANT_COLLECTION

## Como rodar (desenvolvimento)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Swagger UI padrão: `http://127.0.0.1:5000/swagger/`

## Endpoints principais
- POST /chats/new?user_id={user_id} — inicia chat (body: model, message). Retorno: stream; header X-Chat-ID.
- POST /chats/{chat_id}/add?user_id={user_id} — continua chat.
- GET /chats?user_id={user_id} — lista chats.
- GET /chats/{chat_id}?user_id={user_id} — retorna histórico.
- DELETE /chats/{chat_id}/delete?user_id={user_id} — remove chat.

Exemplo (curl, streaming):
```bash
curl -N -X POST "http://127.0.0.1:5000/chats/new?user_id=test" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2-math","message":"Como resolver 2+2?"}'
```

## Swagger / OpenAPI
A documentação OpenAPI/Swagger é gerada pelo template em `configs/swagger_config.py`. A UI é exposta em `/swagger/`. O template atualmente referencia o domínio de deploy; atualize se necessário.
Acesse https://4.206.202.49.nip.io/swagger para visualizar e testar os endpoints.


## Streaming
- Implementado via generator que consome stream do LLM (Ollama).
- Rotas retornam `Response(generator, mimetype='text/plain')` para envio incremental.
- Resposta completa é concatenada e salva no histórico após fim do stream.

## Persistência: MongoDB
- Uso de MongoDB via PyMongo quando `URL_CONNECTION_MONGODB` disponível.
- Timestamps gravados em ISO strings para compatibilidade JSON/Swagger.


## Deployment (Azure)
- A aplicação está deployada em Azure e disponível em: https://4.206.202.49.nip.io
- Deploy configurado com os passos do script `deploy_aprovia.sh`:
  - Instalação de dependências do sistema, Ollama e modelos (qwen2-math, llama3)
  - Instalação e configuração do MongoDB 
  - Criação de venv, instalação de `requirements.txt`
  - Criação de `.env` com valores padrão
  - Criação de service systemd e configuração Nginx + Certbot para TLS
- Consulte o script para detalhes: `deploy_aprovia.sh.sh`

Observações para produção:
- Em produção, confirmar domain/host no `configs/swagger_config.py` caso queira refletir o domínio público.
- Não comitar credenciais no repositório.

## Troubleshooting rápido
- Erro SSL/TLS com Atlas: atualizar `certifi`, `dnspython`, `pymongo` e verificar firewall/proxy.
- Streaming: usar `curl -N` ou cliente que aceite chunked transfer.
- Ollama: confirmar daemon rodando e modelos baixados.

Desenvolvido por [Allan Deyvison, Beatriz Medeiros, Nickolas Aparecido] A API estará disponível em: [https://4.206.202.49.nip.io)

---
