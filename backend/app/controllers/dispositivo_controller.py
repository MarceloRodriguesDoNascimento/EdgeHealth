from flask import Blueprint, jsonify, request

from app.services.dispositivo_service import (
    atualizar_dispositivo,
    criar_dispositivo,
    excluir_dispositivo,
    listar_dispositivos,
)
from app.services.ping_service import registrar_ping


dispositivo_bp = Blueprint("dispositivo", __name__, url_prefix="/dispositivos")


@dispositivo_bp.get("")
def index():
    dispositivos = listar_dispositivos()
    return jsonify([dispositivo.to_dict() for dispositivo in dispositivos])


@dispositivo_bp.post("")
def create():
    dispositivo = criar_dispositivo(request.get_json() or {})
    return jsonify(dispositivo.to_dict()), 201


@dispositivo_bp.put("/<int:dispositivo_id>")
def update(dispositivo_id):
    dispositivo = atualizar_dispositivo(dispositivo_id, request.get_json() or {})
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return jsonify(dispositivo.to_dict())


@dispositivo_bp.delete("/<int:dispositivo_id>")
def destroy(dispositivo_id):
    if not excluir_dispositivo(dispositivo_id):
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return "", 204


@dispositivo_bp.post("/<int:dispositivo_id>/ping")
def ping(dispositivo_id):
    dados = request.get_json() or {}
    dispositivo = registrar_ping(dispositivo_id, dados.get("status", "online"))
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return jsonify(dispositivo.to_dict())
