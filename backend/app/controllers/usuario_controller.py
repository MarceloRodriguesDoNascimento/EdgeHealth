from flask import Blueprint, jsonify, request

from app.services.usuario_service import (
    atualizar_usuario,
    buscar_usuario,
    criar_usuario,
    excluir_usuario,
    listar_usuarios,
)

usuario_bp = Blueprint("usuario", __name__, url_prefix="/usuarios")


@usuario_bp.get("")
def index():
    usuarios = listar_usuarios()
    return jsonify([usuario.to_dict() for usuario in usuarios])


@usuario_bp.get("/<int:usuario_id>")
def show(usuario_id):
    usuario = buscar_usuario(usuario_id)
    if not usuario:
        return jsonify({"erro": "usuario nao encontrado"}), 404
    return jsonify(usuario.to_dict())


@usuario_bp.post("")
def create():
    usuario = criar_usuario(request.get_json() or {})
    return jsonify(usuario.to_dict()), 201


@usuario_bp.put("/<int:usuario_id>")
def update(usuario_id):
    usuario = atualizar_usuario(usuario_id, request.get_json() or {})
    if not usuario:
        return jsonify({"erro": "usuario nao encontrado"}), 404
    return jsonify(usuario.to_dict())


@usuario_bp.delete("/<int:usuario_id>")
def destroy(usuario_id):
    if not excluir_usuario(usuario_id):
        return jsonify({"erro": "usuario nao encontrado"}), 404
    return "", 204
