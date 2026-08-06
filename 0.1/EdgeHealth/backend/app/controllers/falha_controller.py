from flask import Blueprint, jsonify, request

from app.services.falha_service import (
    atualizar_falha,
    buscar_falha,
    criar_falha,
    excluir_falha,
    listar_falhas,
)

falha_bp = Blueprint("falha", __name__, url_prefix="/falhas")


@falha_bp.get("")
def index():
    falhas = listar_falhas()
    return jsonify([falha.to_dict() for falha in falhas])


@falha_bp.get("/<int:falha_id>")
def show(falha_id):
    falha = buscar_falha(falha_id)
    if not falha:
        return jsonify({"erro": "falha nao encontrada"}), 404
    return jsonify(falha.to_dict())


@falha_bp.post("")
def create():
    falha = criar_falha(request.get_json() or {})
    return jsonify(falha.to_dict()), 201


@falha_bp.put("/<int:falha_id>")
def update(falha_id):
    falha = atualizar_falha(falha_id, request.get_json() or {})
    if not falha:
        return jsonify({"erro": "falha nao encontrada"}), 404
    return jsonify(falha.to_dict())


@falha_bp.delete("/<int:falha_id>")
def destroy(falha_id):
    if not excluir_falha(falha_id):
        return jsonify({"erro": "falha nao encontrada"}), 404
    return "", 204
