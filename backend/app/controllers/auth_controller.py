from flask import Blueprint, jsonify, request

from app.services.auth_service import (
    autenticar_usuario,
    gerar_token,
    registrar_usuario,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    dados = request.get_json(silent=True) or {}

    try:
        usuario = registrar_usuario(dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    return jsonify({"usuario": usuario.to_dict()}), 201


@auth_bp.post("/login")
def login():
    dados = request.get_json(silent=True) or {}
    usuario = autenticar_usuario(dados.get("email", ""), dados.get("senha", ""))

    if not usuario:
        return jsonify({"erro": "credenciais invalidas"}), 401

    return jsonify(
        {
            "token": gerar_token(usuario),
            "usuario": usuario.to_dict(),
        }
    )
