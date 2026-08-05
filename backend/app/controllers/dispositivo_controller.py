from flask import Blueprint, jsonify, request

from app.services.dispositivo_service import (
    atualizar_dispositivo,
    criar_dispositivo,
    excluir_dispositivo,
    listar_dispositivos,
    obter_dispositivo,
)
from app.services.ping_service import registrar_ping


dispositivo_bp = Blueprint("dispositivo", __name__, url_prefix="/dispositivos")


@dispositivo_bp.get("")
def index():
    empresa_id = request.args.get("empresa_id", type=int)
    dispositivos = listar_dispositivos(empresa_id=empresa_id)
    return jsonify([dispositivo.to_dict() for dispositivo in dispositivos])


@dispositivo_bp.post("")
def create():
    dados = request.get_json(silent=True) or {}

    try:
        dispositivo = criar_dispositivo(dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    return jsonify(dispositivo.to_dict()), 201


@dispositivo_bp.get("/<int:dispositivo_id>")
def show(dispositivo_id):
    dispositivo = obter_dispositivo(dispositivo_id)
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return jsonify(dispositivo.to_dict())


@dispositivo_bp.patch("/<int:dispositivo_id>")
@dispositivo_bp.put("/<int:dispositivo_id>")
def update(dispositivo_id):
    dados = request.get_json(silent=True) or {}

    try:
        dispositivo = atualizar_dispositivo(dispositivo_id, dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

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
    dados = request.get_json(silent=True) or {}
    resultado = registrar_ping(dispositivo_id, dados)

    if not resultado:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404

    return jsonify(
        {
            "dispositivo": resultado["dispositivo"].to_dict(),
            "metrica": resultado["metrica"].to_dict() if resultado["metrica"] else None,
            "falha": resultado["falha"].to_dict() if resultado["falha"] else None,
        }
    )
