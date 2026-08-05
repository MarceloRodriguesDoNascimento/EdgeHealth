from flask import Blueprint, jsonify, request

from app import db
from app.models import Metrica


metrica_bp = Blueprint("metrica", __name__, url_prefix="/metricas")


@metrica_bp.get("")
def index():
    metricas = Metrica.query.all()
    return jsonify([metrica.to_dict() for metrica in metricas])


@metrica_bp.post("")
def create():
    dados = request.get_json() or {}
    metrica = Metrica(
        dispositivo_id=dados["dispositivo_id"],
        tipo=dados["tipo"],
        valor=dados["valor"],
    )
    db.session.add(metrica)
    db.session.commit()
    return jsonify(metrica.to_dict()), 201
