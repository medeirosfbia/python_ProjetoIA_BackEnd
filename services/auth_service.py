import base64
import os

import jwt
from flask import g, jsonify, request


def _jwt_key() -> bytes:
    secret = os.getenv("JWT_SECRET_B64")
    if not secret:
        raise RuntimeError("JWT_SECRET_B64 não configurado")

    try:
        return base64.b64decode(secret, validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError("JWT_SECRET_B64 inválido") from error


def authenticate_request():
    public_paths = (
        "/swagger/",
        "/flasgger_static/",
        "/apispec_1.json",
    )
    if request.method == "OPTIONS" or request.path.startswith(public_paths):
        return None

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return jsonify({"error": "Token de autenticação obrigatório"}), 401

    try:
        claims = jwt.decode(
            token,
            _jwt_key(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except (jwt.InvalidTokenError, RuntimeError):
        return jsonify({"error": "Token inválido ou expirado"}), 401

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        return jsonify({"error": "Token sem usuário válido"}), 401

    g.user_id = subject
    g.jwt_claims = claims
    return None


def authenticated_user_id() -> str:
    user_id = request.args.get("user_id")
    if user_id and user_id != g.user_id:
        raise PermissionError("O usuário informado não corresponde ao token")
    return g.user_id