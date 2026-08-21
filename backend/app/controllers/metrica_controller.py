from flask import Blueprint, jsonify, request

from app.services.metrica_service import (
    atualizar_metrica,
    buscar_metrica,
    criar_metrica,
    excluir_metrica,
    listar_metricas,
)


metrica_bp = Blueprint("metrica", __name__, url_prefix="/metricas")


@metrica_bp.get("")
def index():
    metricas = listar_metricas()
    return jsonify([metrica.to_dict() for metrica in metricas])


@metrica_bp.get("/<int:metrica_id>")
def show(metrica_id):
    metrica = buscar_metrica(metrica_id)
    if not metrica:
        return jsonify({"erro": "metrica nao encontrada"}), 404
    return jsonify(metrica.to_dict())


@metrica_bp.post("")
def create():
    metrica = criar_metrica(request.get_json() or {})
    return jsonify(metrica.to_dict()), 201


@metrica_bp.put("/<int:metrica_id>")
def update(metrica_id):
    metrica = atualizar_metrica(metrica_id, request.get_json() or {})
    if not metrica:
        return jsonify({"erro": "metrica nao encontrada"}), 404
    return jsonify(metrica.to_dict())


@metrica_bp.delete("/<int:metrica_id>")
def destroy(metrica_id):
    if not excluir_metrica(metrica_id):
        return jsonify({"erro": "metrica nao encontrada"}), 404
    return "", 204
