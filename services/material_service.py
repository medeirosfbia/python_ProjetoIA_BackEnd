import os
import re
import unicodedata
from datetime import datetime, timezone

from azure.core import MatchConditions
from azure.core.exceptions import (
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
)
from werkzeug.utils import secure_filename

from models import material as material_model

# Extensão -> content type gravado no blob (não confiamos no tipo enviado pelo cliente)
TIPOS_PERMITIDOS = {
    "pdf": "application/pdf",
    "txt": "text/plain; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

CONTEUDO_REGEX = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


class MaterialValidationError(ValueError):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


class MaterialConflictError(Exception):
    pass


def _max_size_bytes() -> int:
    return int(os.getenv("MATERIALS_MAX_SIZE_MB", "50")) * 1024 * 1024


def normalize_conteudo(conteudo) -> str:
    """'Matemática Básica' -> 'matematica-basica'. Cada conteúdo é uma pasta no container."""
    if not isinstance(conteudo, str):
        raise MaterialValidationError(["conteudo é obrigatório"])
    ascii_text = (
        unicodedata.normalize("NFKD", conteudo)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[\s]+", "-", ascii_text.strip().lower())
    if not CONTEUDO_REGEX.match(slug):
        raise MaterialValidationError([
            "conteudo deve ter até 63 caracteres: letras, números, '-' ou '_'"
        ])
    return slug


def _normalize_nome(nome) -> str:
    seguro = secure_filename(nome or "")
    base, ponto, extensao = seguro.rpartition(".")
    if not ponto or not base:
        raise MaterialValidationError(["nome de arquivo inválido"])
    extensao = extensao.lower()
    if extensao not in TIPOS_PERMITIDOS:
        raise MaterialValidationError([
            f"extensão .{extensao} não permitida; use: {', '.join(sorted(TIPOS_PERMITIDOS))}"
        ])
    return f"{base}.{extensao}"


def _path(conteudo: str, nome: str) -> str:
    return f"{normalize_conteudo(conteudo)}/{_normalize_nome(nome)}"


def _file_length(arquivo) -> int:
    stream = arquivo.stream
    stream.seek(0, os.SEEK_END)
    length = stream.tell()
    stream.seek(0)
    return length


def _validate_file(arquivo, nome_destino: str):
    """Valida o arquivo enviado e retorna (stream, tamanho, content_type)."""
    if arquivo is None or not arquivo.filename:
        raise MaterialValidationError(["envie o arquivo no campo multipart 'arquivo'"])

    extensao_destino = nome_destino.rpartition(".")[2]
    extensao_enviada = _normalize_nome(arquivo.filename).rpartition(".")[2]
    if extensao_enviada != extensao_destino:
        raise MaterialValidationError([
            f"o arquivo enviado (.{extensao_enviada}) deve ter a mesma extensão de {nome_destino}"
        ])

    length = _file_length(arquivo)
    if length == 0:
        raise MaterialValidationError(["o arquivo está vazio"])
    if length > _max_size_bytes():
        raise MaterialValidationError([
            f"o arquivo excede o limite de {os.getenv('MATERIALS_MAX_SIZE_MB', '50')} MB"
        ])
    return arquivo.stream, length, TIPOS_PERMITIDOS[extensao_destino]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Leitura (qualquer usuário autenticado)
# ---------------------------------------------------------------------------

def list_folders() -> list:
    return material_model.list_folders()


def list_materials(conteudo: str = None) -> list:
    return material_model.list_materials(normalize_conteudo(conteudo) if conteudo else None)


def get_material(conteudo: str, nome: str):
    return material_model.get_material(_path(conteudo, nome))


def download_material(conteudo: str, nome: str):
    return material_model.download_material(_path(conteudo, nome))


# ---------------------------------------------------------------------------
# Escrita (somente admins; checado no controller)
# ---------------------------------------------------------------------------

def create_material(conteudo: str, arquivo, user_id: str) -> dict:
    path = _path(conteudo, arquivo.filename if arquivo else None)
    stream, length, content_type = _validate_file(arquivo, path.rpartition("/")[2])
    agora = _now_iso()
    metadata = {
        "enviado_por": user_id,
        "enviado_em": agora,
        "atualizado_por": user_id,
        "atualizado_em": agora,
    }
    try:
        return material_model.upload_material(
            path, stream, length, content_type, metadata, overwrite=False
        )
    except ResourceExistsError as error:
        raise MaterialConflictError(
            f"Já existe o arquivo {path}; use PUT para substituí-lo"
        ) from error


def update_material(conteudo: str, nome: str, arquivo, user_id: str):
    """Substitui o conteúdo de um arquivo existente. Retorna None se ele não existir."""
    path = _path(conteudo, nome)
    atual = material_model.get_material(path)
    if not atual:
        return None

    stream, length, content_type = _validate_file(arquivo, path.rpartition("/")[2])
    metadata = {
        **atual["metadata"],
        "atualizado_por": user_id,
        "atualizado_em": _now_iso(),
    }
    try:
        # IfPresent: não recria o arquivo se ele for excluído entre a checagem e o upload
        return material_model.upload_material(
            path, stream, length, content_type, metadata,
            overwrite=True, match_condition=MatchConditions.IfPresent,
        )
    except (ResourceModifiedError, ResourceNotFoundError):
        return None


def delete_material(conteudo: str, nome: str) -> bool:
    return material_model.delete_material(_path(conteudo, nome))
