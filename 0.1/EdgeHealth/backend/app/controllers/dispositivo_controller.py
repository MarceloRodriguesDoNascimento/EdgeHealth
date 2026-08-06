from flask import Blueprint, jsonify, request

from app.services.dispositivo_service import DispositivoService
from app.services.ping_service import registrar_ping


dispositivo_bp = Blueprint("dispositivo", __name__, url_prefix="/dispositivos")


@dispositivo_bp.get("")
def index():
    dispositivos = DispositivoService.listar_todos()
    return jsonify([dispositivo.to_dict() for dispositivo in dispositivos])


@dispositivo_bp.get("/<int:dispositivo_id>")
def show(dispositivo_id):
    dispositivo = DispositivoService.buscar_por_id(dispositivo_id)
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return jsonify(dispositivo.to_dict())


@dispositivo_bp.post("")
def create():
    dados = request.get_json() or {}
    if not dados.get("nome") or not dados.get("ip"):
        return jsonify({"erro": "Os campos nome e ip são obrigatórios."}), 400

    dispositivo = DispositivoService.criar(dados)
    return jsonify(dispositivo.to_dict()), 201


@dispositivo_bp.put("/<int:dispositivo_id>")
def update(dispositivo_id):
    dados = request.get_json() or {}
    dispositivo = DispositivoService.atualizar(dispositivo_id, dados)
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return jsonify(dispositivo.to_dict())


@dispositivo_bp.delete("/<int:dispositivo_id>")
def destroy(dispositivo_id):
    sucesso = DispositivoService.deletar(dispositivo_id)
    if not sucesso:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return "", 204


@dispositivo_bp.post("/<int:dispositivo_id>/ping")
def ping(dispositivo_id):
    dados = request.get_json() or {}
    dispositivo = registrar_ping(dispositivo_id, dados.get("status", "online"))
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404
    return jsonify(dispositivo.to_dict())
