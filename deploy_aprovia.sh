#!/bin/bash

set -e

# ================================
# CONFIGURAÇÕES DO SISTEMA
# ================================
USERNAME="aproviauser"
PROJECT_NAME="aprovia"
PROJECT_DIR="/home/$USERNAME/$PROJECT_NAME"
REPO_URL="https://github.com/AllanDeyvison/python_ProjetoIA_BackEnd"
DOMAIN="4.206.202.49.nip.io"
EMAIL="allan.13dias@gmail.com"

echo "==== INICIANDO DEPLOY AUTOMÁTICO APROVIA ===="

# ================================
# ATUALIZAR SISTEMA
# ================================
sudo apt update && sudo apt upgrade -y
sudo apt install -y git build-essential python3 python3-venv python3-pip curl ca-certificates netcat-openbsd nginx certbot python3-certbot-nginx

# ================================
# INSTALAR OLLAMA
# ================================
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl start ollama

ollama pull llama3
ollama pull qwen2-math
ollama pull nomic-embed-text

# ================================
# INSTALAR MONGODB 7
# ================================
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

echo "deb [signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt update
sudo apt install -y mongodb-org

sudo systemctl enable mongod
sudo systemctl start mongod

# ================================
# CLONAR O PROJETO
# ================================
mkdir -p /home/$USERNAME
cd /home/$USERNAME

if [ ! -d "$PROJECT_DIR" ]; then
    git clone $REPO_URL $PROJECT_NAME
fi

cd $PROJECT_DIR

# ================================
# CRIAR VENV E INSTALAR DEPENDÊNCIAS
# ================================
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# ================================
# CRIAR ARQUIVO .env
# ================================
cat <<EOF > .env
TEMP_FOLDER='./_temp'
CHROMA_PATH='chroma'
COLLECTION_NAME='local-test'
LLM_MODEL='qwen2-math'
TEXT_EMBEDDING_MODEL='nomic-embed-text'
URL_CONNECTION_MONGODB='mongodb://localhost:27017/'
DATABASE_NAME='aprovia_db'
ASSISTANT_COLLECTION='math_assistant'
EOF

# ================================
# CRIAR SERVIÇO SYSTEMD
# ================================
sudo bash -c "cat <<EOF > /etc/systemd/system/aprovia.service
[Unit]
Description=Aprovia Python Backend
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=$PROJECT_DIR
Environment=\"PATH=$PROJECT_DIR/venv/bin\"
ExecStart=$PROJECT_DIR/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable aprovia
sudo systemctl start aprovia

# ================================
# CONFIGURAR NGINX
# ================================
sudo bash -c "cat <<EOF > /etc/nginx/sites-available/$PROJECT_NAME
server {
    listen 80;
    server_name $DOMAIN;

    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_request_buffering off;
        client_max_body_size 20M;

        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}
EOF"

sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/

sudo nginx -t && sudo systemctl restart nginx

# ================================
# CERTBOT – GERAR HTTPS
# ================================
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL

echo "==== DEPLOY COMPLETO ===="
echo "Backend rodando em: https://$DOMAIN"
