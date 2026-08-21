from flask import Blueprint, jsonify, request

from app.services.auth_service import autenticar_usuario


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/login")
def login():
    dados = request.get_json() or {}
    usuario = autenticar_usuario(dados.get("email"), dados.get("senha"))

    if not usuario:
        return jsonify({"erro": "credenciais invalidas"}), 401

    return jsonify(usuario.to_dict())
