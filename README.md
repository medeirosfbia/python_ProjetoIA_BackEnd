## Bibliotecas PyPI necessárias
- Flask
- Flask-Cors
- langchain
- langchain-text-splitters
- langchain-community
- dotenv
- chromadb
- unstructured
- "unstructured[all-docs]"
- ollama
- pymongo


```bash
python3 -m venv venv
```

```bash
# Windows
venv\Scripts\activate
```

Para a query:
```bash
pip install Flask Flask-Cors ollama pymongo dotenv
```

Para o embed:
```bash
pip install langchain langchain-text-splitters langchain-community langchain-ollama langchain-chroma chromadb unstructured 
```

```bash
pip install "unstructured[all-docs]"
```

E use o env.txt para criar seu .env com suas variáveis de ambiente.
