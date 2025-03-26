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
pip install Flask Flask-Cors ollama
```

Para o embed:
```bash
pip install dotenv langchain langchain-text-splitters langchain-community chromadb unstructured pymongo
```

```bash
pip install "unstructured[all-docs]"
```

E use o sampleenv.txt para criar seu .env com suas variáveis de ambiente.
