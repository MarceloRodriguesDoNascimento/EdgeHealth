from flask import Blueprint, jsonify

from app import db
from app.controllers import auth_bp, dispositivo_bp, metrica_bp


api_bp = Blueprint("api", __name__)

api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(dispositivo_bp)
api_bp.register_blueprint(metrica_bp)


@api_bp.get("/health")
def healthcheck():
    return jsonify({"status": "ok", "service": "edgehealth-api"})


@api_bp.post("/database/create")
def create_database():
    db.create_all()
    return jsonify({"status": "created"})
