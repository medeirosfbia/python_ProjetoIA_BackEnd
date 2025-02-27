from flask import Flask, jsonify, request
from flask_cors import CORS
from query import query
# from addDocuments import addDocs

app = Flask(__name__)
CORS(app) # Isso habilita o CORS para todas as rotas

@app.route('/query', methods=['POST'])
def hello():
    data = request.get_json()
    response = query(data.get('message'))

    if response:
        return jsonify({"answer": response}), 200
    else:
        return jsonify({"error": "Something went wrong"}), 400



if __name__ == "__main__":
    app.run()