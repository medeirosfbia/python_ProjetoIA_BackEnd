from flask import Flask, jsonify, request
from query import query

app = Flask(__name__)

@app.route('/query', methods=['POST'])
def hello():
    data = request.get_json()
    response = query(data.get('query'))

    if response:
        return jsonify({"answer": response}), 200
    else:
        return jsonify({"error": "Something went wrong"}), 400



if __name__ == "__main__":
    app.run()