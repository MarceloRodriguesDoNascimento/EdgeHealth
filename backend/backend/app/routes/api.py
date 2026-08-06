from flask import Blueprint, jsonify

from app.controllers import (
    auth_bp,
    dispositivo_bp,
    empresa_bp,
    falha_bp,
    metrica_bp,
    usuario_bp,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(dispositivo_bp)
api_bp.register_blueprint(empresa_bp)
api_bp.register_blueprint(usuario_bp)
api_bp.register_blueprint(metrica_bp)
api_bp.register_blueprint(falha_bp)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})