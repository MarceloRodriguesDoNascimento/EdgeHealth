import secrets
from flask import current_app
from werkzeug.exceptions import Forbidden, Unauthorized
from models import AuthSession, Usuario, utcnow
from services.comum.hash_token import HashToken


class ValidarSessaoService:
    """Session cookie, CSRF token on writes, current Terms of Use and the admin role."""

    def executar(self, token, csrf, metodo, admin=False, termos=True):
        session = AuthSession.buscar_por_id(HashToken.sha256(token)) if token else None
        user = Usuario.buscar_por_id(session.usuario_id) if session else None
        if not session or session.expires_at <= utcnow() or not user or not user.ativo:
            raise Unauthorized('Sessão expirada. Entre novamente.')
        if metodo not in ('GET', 'HEAD', 'OPTIONS'):
            if not csrf or not secrets.compare_digest(HashToken.sha256(csrf), session.csrf_hash):
                raise Forbidden('Requisição inválida. Atualize a página e tente novamente.')
        if termos and user.termos_versao != current_app.config['TERMS_VERSION']:
            raise Forbidden('Aceite a versão atual dos Termos de Uso para continuar.')
        if admin and user.papel != 'ADMIN':
            raise Forbidden('Esta operação exige um administrador da empresa.')
        return user, session
