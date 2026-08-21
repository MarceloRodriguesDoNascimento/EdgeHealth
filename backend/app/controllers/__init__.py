from app.controllers.auth_controller import auth_bp
from app.controllers.dispositivo_controller import dispositivo_bp
from app.controllers.empresa_controller import empresa_bp
from app.controllers.falha_controller import falha_bp
from app.controllers.metrica_controller import metrica_bp
from app.controllers.usuario_controller import usuario_bp


__all__ = [
    "auth_bp",
    "dispositivo_bp",
    "empresa_bp",
    "falha_bp",
    "metrica_bp",
    "usuario_bp",
]
