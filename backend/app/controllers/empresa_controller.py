from flask import Blueprint, jsonify, request

from app.services.empresa_service import (
    atualizar_empresa,
    buscar_empresa,
    criar_empresa,
    excluir_empresa,
    listar_empresas,
)

empresa_bp = Blueprint("empresa", __name__, url_prefix="/empresas")


@empresa_bp.get("")
def index():
    empresas = listar_empresas()
    return jsonify([empresa.to_dict() for empresa in empresas])


@empresa_bp.get("/<int:empresa_id>")
def show(empresa_id):
    empresa = buscar_empresa(empresa_id)
    if not empresa:
        return jsonify({"erro": "empresa nao encontrada"}), 404
    return jsonify(empresa.to_dict())


@empresa_bp.post("")
def create():
    empresa = criar_empresa(request.get_json() or {})
    return jsonify(empresa.to_dict()), 201


@empresa_bp.put("/<int:empresa_id>")
def update(empresa_id):
    empresa = atualizar_empresa(empresa_id, request.get_json() or {})
    if not empresa:
        return jsonify({"erro": "empresa nao encontrada"}), 404
    return jsonify(empresa.to_dict())


@empresa_bp.delete("/<int:empresa_id>")
def destroy(empresa_id):
    if not excluir_empresa(empresa_id):
        return jsonify({"erro": "empresa nao encontrada"}), 404
    return "", 204
