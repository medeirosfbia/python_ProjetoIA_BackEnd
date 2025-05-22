# Importando as bibliotecas necessárias para o script
import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# Variáveis de ambiente que serão utilizadas pelo código
CHROMA_PATH = os.getenv('CHROMA_PATH')
COLLECTION_NAME = os.getenv('COLLECTION_NAME')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL')

def get_vector_db():
    """
    Cria um banco de dados de vetores usando o modelo de gerador de embeddings especificado.
    Primeiro, configura a geração das embeddings com o modelo e a barra de progresso.
    Em seguida, cria uma instância do Chroma que permite armazenar e recuperar informações usando vetores,
    especificando o nome da coleção e o diretório de persistência.
    A função retorna este banco de dados de vetores como resultado final.
    """

    # Configura a geração das embeddings utilizando o modelo fornecido
    embbeding = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL)

    db = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_PATH,
        embedding_function=embbeding
    )

    return db