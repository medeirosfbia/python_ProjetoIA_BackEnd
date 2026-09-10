import json
import base64
from datetime import datetime, timezone
from flask import jsonify, request
from config.azure_config import queue_client

def registrar_novo_chat():
    try:
        data = request.get_json()
        
        id_venda = data.get("idVenda")
        cliente = data.get("cliente")
        valor_total = data.get("valorTotal")
        itens = data.get("itens", [])

        if not id_venda or not cliente or valor_total is None:
            return jsonify({"message": "Dados incompletos da transação."}), 400

        # Monta a estrutura da transação
        transacao = {
            "idVenda": id_venda,
            "cliente": cliente,
            "valorTotal": valor_total,
            "itens": itens,
            "status": "AGUARDANDO_NOTA_FISCAL",
            "dataHora": datetime.now(timezone.utc).isoformat()
        }

        # Converte o dicionário Python para String JSON
        mensagem_json = json.dumps(transacao)

        # Converte para Base64 (Requisito padrão do Azure Queue)
        mensagem_base64 = base64.b64encode(mensagem_json.encode('utf-8')).decode('utf-8')

        # Envia para a fila do Azure
        response = queue_client.send_message(mensagem_base64)

        print(f"Venda {id_venda} enviada à fila. Message ID: {response.id}")

        return jsonify({
            "message": "Venda confirmada com sucesso! Dados enviados para geração de nota fiscal.",
            "messageId": response.id,
            "transacao": transacao
        }), 200

    except Exception as e:
        print(f"Erro ao enviar mensagem para a fila: {e}")
        return jsonify({"message": "Erro ao processar a confirmação de venda."}), 500


def listar_mensagens_fila():
    try:
        # Espia até 10 mensagens sem removê-las da fila
        messages = queue_client.peek_messages(max_messages=10)
        mensagens_formatadas = []

        for msg in messages:
            # Decodifica de Base64 para texto JSON
            texto_decodificado = base64.b64str(msg.content).decode('utf-8') if hasattr(base64, 'b64str') else base64.b64decode(msg.content).decode('utf-8')
            
            mensagens_formatadas.append({
                "messageId": msg.id,
                "insertedOn": msg.inserted_on.isoformat() if msg.inserted_on else None,
                "conteudo": json.loads(texto_decodificado)
            })

        return jsonify(mensagens_formatadas), 200

    except Exception as e:
        print(f"Erro ao ler fila: {e}")
        return jsonify({"message": "Erro ao consultar a fila do Azure."}), 500