from flask import Blueprint, jsonify

from app.controllers import auth_bp, dispositivo_bp, metrica_bp


api_bp = Blueprint("api", __name__)
api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(dispositivo_bp)
api_bp.register_blueprint(metrica_bp)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})
