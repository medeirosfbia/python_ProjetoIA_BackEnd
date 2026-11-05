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
- Notificações push
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

### Provas
Criar, editar e deletar provas é permitido só para admins: quem tem o claim `role`/`roles`
com `ADMIN` no JWT ou cujo username está em `ADMIN_USERS` no `.env`. Usuários comuns
veem só provas com status `APROVADO` e sem o gabarito.
- GET /exams?assunto=... — lista provas (resumo, sem questões).
- GET /exams/{exam_id} — retorna a prova.
- POST /exams — cria prova (admin).
- PUT /exams/{exam_id} — substitui a prova (admin).
- DELETE /exams/{exam_id} — remove a prova (admin); as respostas já enviadas são mantidas.
- POST /exams/{exam_id}/answers — envia respostas; múltipla escolha é corrigida na hora,
  dissertativas e desafios de código ficam pendentes. Cada envio vira uma tentativa na
  coleção `exam_answers`.
- GET /exams/{exam_id}/answers — tentativas do usuário nesta prova.
- GET /exams/answers — histórico de desempenho do usuário em todas as provas.
- GET /exams/{exam_id}/answers/all — tentativas de todos os usuários (admin).

### Materiais das matérias (Azure Blob)
Arquivos (PDF, DOCX, PPTX, XLSX, TXT, MD, CSV, imagens) guardados no container
`MATERIALS_CONTAINER` (padrão `aprovia-materiais`, criado privado no primeiro uso), com uma
pasta por conteúdo: `matematica/aula.pdf`, `ingles/verbos.pdf`. O nome do conteúdo é
normalizado (`Matemática Básica` → `matematica-basica`). Serão usados como fonte do RAG.
Todo usuário autenticado pode ler; enviar, substituir e deletar é só para admins.
- GET /materials/folders — lista as pastas (conteúdos).
- GET /materials?conteudo=... — lista os arquivos (todos ou de uma pasta).
- GET /materials/{conteudo}/{nome} — dados do arquivo (tamanho, tipo, quem enviou).
- GET /materials/{conteudo}/{nome}/download — arquivo em streaming (`?download=1` força o download).
- POST /materials/{conteudo} — envia arquivo (admin; multipart, campo `arquivo`). 409 se já existir.
- PUT /materials/{conteudo}/{nome} — substitui o arquivo, mesma extensão (admin).
- DELETE /materials/{conteudo}/{nome} — remove o arquivo (admin).

```bash
curl -X POST "http://127.0.0.1:5000/materials/matematica" \
  -H "Authorization: Bearer $TOKEN" -F "arquivo=@equacoes.pdf"
```

### Notificações push (app mobile)
Resumo das rotas (detalhes em [Notificações push](#notificações-push)):

- POST /notifications/tokens — cadastra o aparelho do usuário logado.
- DELETE /notifications/tokens — remove o aparelho do usuário logado.
- POST /notifications/send — notificação avulsa (admin).

Para gravar a prova de exemplo (`seeds/exam_example.json`) no MongoDB do `.env`:
```bash
python -m seeds.seed_exam_example
```

Para habilitar a mensageria do histórico, configure `AZURE_STORAGE_CONNECTION_STRING`
no `.env`. Opcionalmente, altere o nome da fila com `AZURE_QUEUE_NAME`. Cada mensagem
salva no histórico é publicada automaticamente na fila para consumo posterior.

Exemplo (curl, streaming):
```bash
curl -N -X POST "http://127.0.0.1:5000/chats/new?user_id=test" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2-math","message":"Como resolver 2+2?"}'
```

## Notificações push

A API não envia o push diretamente: guarda os aparelhos dos usuários (coleção
`push_tokens`) e publica um evento na fila `aprovia-notifications`. Quem entrega
ao celular, via Expo Push, é a Azure Function em `consumers_messaging`. Corpos,
respostas e códigos de erro de cada rota estão no Swagger.

| Arquivo | O que faz |
|---|---|
| `controllers/notification_controller.py` | Converte o resultado em HTTP (201/200, 400, 403, 404, 503). |
| `services/notification_service.py` | Valida token, plataforma e envio avulso; monta as notificações automáticas. |
| `models/push_token.py` | Grava (upsert pelo token) e remove o token do usuário no MongoDB. |
| `messaging/queue_notification_producer.py` | Publica o evento na fila em JSON Base64, como o histórico. |
| `configs/azure_config.py` | Cria o cliente (e a fila, se não existir) de notificações. |

Regras principais:

- O app cadastra o token após o login e o remove no logout, antes de descartar o JWT.
- Se outra conta entrar no mesmo aparelho, o token passa a ser dela.
- Notificações automáticas: prova que passa a `APROVADO` (`data.type = exam_published`,
  só na transição, não a cada edição) e material enviado (`data.type = material_created`).
- Uma falha na fila nas notificações automáticas só gera log: a prova ou o material
  continuam salvos.
- Lembrete diário: o `authenticate_request` registra o dia (fuso `REMINDER_TIMEZONE`)
  em que o usuário fez a primeira requisição autenticada (coleção `user_activity`,
  `services/activity_service.py`). Um cache em memória faz gravar no MongoDB só uma
  vez por usuário por dia; falha na gravação só gera log. A Function usa isso para
  lembrar, às 15h, quem ainda não entrou.

Variáveis (opcionais; devem ser iguais na Function): `NOTIFICATIONS_QUEUE_NAME`
(padrão `aprovia-notifications`), `PUSH_TOKENS_COLLECTION` (padrão `push_tokens`),
`USER_ACTIVITY_COLLECTION` (padrão `user_activity`) e `REMINDER_TIMEZONE`
(padrão `America/Sao_Paulo`).

### Testes (`tests/test_notifications.py`)

Usam mocks; não acessam MongoDB, fila nem Expo.

| Grupo | O que cobre |
|---|---|
| `NotificationEndpointsTestCase` | Cadastro (201; token/plataforma/corpo inválidos → 400), remoção (200; token de outro usuário → 404) e envio avulso (não admin → 403, padrão `"all"` → 202, validação → 400, fila fora → 503). |
| `NotificationServiceTestCase` | Destinatários sem repetição, formatos de token aceitos/rejeitados, notificação automática que nunca lança erro, conteúdo da notificação de prova e formato Base64 do produtor. |
| `test_activity.py` | Uma gravação por usuário por dia, nova gravação no dia seguinte, falha no MongoDB não quebra a requisição, "hoje" no fuso de São Paulo, token válido registra atividade e token inválido não. |
| `NotificationTriggersTestCase` | Prova criada `APROVADO` notifica; `RASCUNHO` não; `RASCUNHO` → `APROVADO` notifica uma única vez; material enviado notifica. |

Rodar os testes com `AZURE_STORAGE_CONNECTION_STRING` preenchida cria a fila
`aprovia-notifications` na conta (o `azure_config.py` cria as filas ao ser importado),
mas nenhuma mensagem é publicada.

## Swagger / OpenAPI
A documentação OpenAPI/Swagger é gerada pelo template em `configs/swagger_config.py`. A UI é exposta em `/swagger/`. O template atualmente referencia o domínio de deploy; atualize se necessário.
Acesse https://4.206.202.49.nip.io/swagger para visualizar e testar os endpoints.


## Streaming
- Implementado via generator que consome stream do LLM (Ollama).
- Rotas retornam `Response(generator, mimetype='text/plain')` para envio incremental.
- Resposta completa é concatenada e salva no histórico após fim do stream.

## Persistência: MongoDB


## Deployment (Azure)
 do chat é publicada automaticamente na fila; o consumidor será responsável por
 persistir no MongoDB posteriormente.
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
