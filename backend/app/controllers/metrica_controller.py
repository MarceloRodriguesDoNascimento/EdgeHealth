from flask import Blueprint, jsonify, request

from app import db
from app.models import Dispositivo, HistoricoFalha, Metrica


metrica_bp = Blueprint("metrica", __name__, url_prefix="/metricas")


@metrica_bp.get("/dispositivo/<int:dispositivo_id>")
def listar_por_dispositivo(dispositivo_id):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404

    metricas = (
        Metrica.query.filter_by(dispositivo_id=dispositivo_id)
        .order_by(Metrica.coletada_em.desc())
        .limit(100)
        .all()
    )
    return jsonify([metrica.to_dict() for metrica in metricas])


@metrica_bp.post("/dispositivo/<int:dispositivo_id>")
def criar_para_dispositivo(dispositivo_id):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if not dispositivo:
        return jsonify({"erro": "dispositivo nao encontrado"}), 404

    dados = request.get_json(silent=True) or {}
    metrica = Metrica(
        dispositivo_id=dispositivo_id,
        cpu_percent=dados.get("cpu_percent"),
        memoria_percent=dados.get("memoria_percent"),
        disco_percent=dados.get("disco_percent"),
        temperatura_c=dados.get("temperatura_c"),
        latencia_ms=dados.get("latencia_ms"),
    )

    db.session.add(metrica)
    db.session.commit()
    return jsonify(metrica.to_dict()), 201


@metrica_bp.get("/falhas/dispositivo/<int:dispositivo_id>")
def listar_falhas(dispositivo_id):
    falhas = (
        HistoricoFalha.query.filter_by(dispositivo_id=dispositivo_id)
        .order_by(HistoricoFalha.ocorreu_em.desc())
        .limit(100)
        .all()
    )
    return jsonify([falha.to_dict() for falha in falhas])
