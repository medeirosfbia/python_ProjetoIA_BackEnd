import os
from functools import lru_cache
from urllib.parse import quote, unquote

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from configs.azure_config import AZURE_STORAGE_CONNECTION_STRING

MATERIALS_CONTAINER = os.getenv("MATERIALS_CONTAINER", "aprovia-materiais")


class MaterialStorageUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _container():
    """Cliente do container, criado (privado) no primeiro uso."""
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise MaterialStorageUnavailable(
            "AZURE_STORAGE_CONNECTION_STRING não configurada"
        )

    container = BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING
    ).get_container_client(MATERIALS_CONTAINER)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    return container


def _to_dict(blob) -> dict:
    conteudo, _, nome = blob.name.partition("/")
    return {
        "conteudo": conteudo,
        "nome": nome,
        "caminho": blob.name,
        "tamanho_bytes": blob.size,
        "content_type": blob.content_settings.content_type,
        "atualizado_em": blob.last_modified.isoformat() if blob.last_modified else None,
        "metadata": {chave: unquote(valor) for chave, valor in (blob.metadata or {}).items()},
    }


def list_folders() -> list:
    return [
        prefix.name.rstrip("/")
        for prefix in _container().walk_blobs(delimiter="/")
        if prefix.name.endswith("/")
    ]


def list_materials(conteudo: str = None) -> list:
    prefix = f"{conteudo}/" if conteudo else None
    return [
        _to_dict(blob)
        for blob in _container().list_blobs(name_starts_with=prefix, include=["metadata"])
    ]


def get_material(path: str):
    try:
        return _to_dict(_container().get_blob_client(path).get_blob_properties())
    except ResourceNotFoundError:
        return None


def download_material(path: str):
    """Retorna o downloader em streaming, ou None se o arquivo não existir."""
    try:
        return _container().get_blob_client(path).download_blob()
    except ResourceNotFoundError:
        return None


def upload_material(path: str, stream, length: int, content_type: str,
                    metadata: dict, overwrite: bool, match_condition=None) -> dict:
    """Grava o arquivo. Com overwrite=False lança ResourceExistsError se já existir."""
    blob = _container().get_blob_client(path)
    extra = {"match_condition": match_condition} if match_condition else {}
    blob.upload_blob(
        stream,
        length=length,
        overwrite=overwrite,
        content_settings=ContentSettings(content_type=content_type),
        # Metadata do Azure só aceita ASCII; usernames podem ter acento
        metadata={chave: quote(str(valor)) for chave, valor in metadata.items()},
        **extra,
    )
    return _to_dict(blob.get_blob_properties())


def delete_material(path: str) -> bool:
    try:
        _container().get_blob_client(path).delete_blob(delete_snapshots="include")
        return True
    except ResourceNotFoundError:
        return False
