from urllib.parse import quote

from flask import Response, jsonify, request

from models.material import MaterialStorageUnavailable
from services.auth_service import authenticated_user_id, is_admin
from services.material_service import (
    MaterialConflictError,
    MaterialValidationError,
    create_material,
    delete_material,
    download_material,
    get_material,
    list_folders,
    list_materials,
    update_material,
)


def _forbidden():
    return jsonify({"error": "Acesso restrito a administradores"}), 403


def _not_found():
    return jsonify({"error": "Material não encontrado"}), 404


def _validation_error(error):
    return jsonify({"error": "Dados inválidos", "detalhes": error.errors}), 400


def _storage_unavailable():
    return jsonify({"error": "Armazenamento de materiais indisponível"}), 503


def _uploaded_file():
    return request.files.get("arquivo")


def _handle_errors(action):
    """Converte os erros comuns do serviço em respostas HTTP."""
    try:
        return action()
    except MaterialValidationError as error:
        return _validation_error(error)
    except MaterialConflictError as error:
        return jsonify({"error": str(error)}), 409
    except MaterialStorageUnavailable:
        return _storage_unavailable()


def list_material_folders_controller():
    return _handle_errors(lambda: (jsonify(list_folders()), 200))


def list_materials_controller():
    return _handle_errors(
        lambda: (jsonify(list_materials(request.args.get("conteudo"))), 200)
    )


def get_material_controller(conteudo, nome):
    def action():
        material = get_material(conteudo, nome)
        if not material:
            return _not_found()
        return jsonify(material), 200
    return _handle_errors(action)


def download_material_controller(conteudo, nome):
    def action():
        downloader = download_material(conteudo, nome)
        if downloader is None:
            return _not_found()
        disposition = "attachment" if request.args.get("download") == "1" else "inline"
        filename = downloader.name.rpartition("/")[2]
        return Response(
            downloader.chunks(),
            mimetype=downloader.properties.content_settings.content_type,
            headers={
                "Content-Length": str(downloader.size),
                "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename)}",
            },
        )
    return _handle_errors(action)


def create_material_controller(conteudo):
    if not is_admin():
        return _forbidden()
    return _handle_errors(lambda: (
        jsonify(create_material(conteudo, _uploaded_file(), authenticated_user_id())),
        201,
    ))


def update_material_controller(conteudo, nome):
    if not is_admin():
        return _forbidden()

    def action():
        material = update_material(conteudo, nome, _uploaded_file(), authenticated_user_id())
        if not material:
            return _not_found()
        return jsonify(material), 200
    return _handle_errors(action)


def delete_material_controller(conteudo, nome):
    if not is_admin():
        return _forbidden()

    def action():
        if not delete_material(conteudo, nome):
            return _not_found()
        return jsonify({"success": "Material deletado com sucesso"}), 200
    return _handle_errors(action)
