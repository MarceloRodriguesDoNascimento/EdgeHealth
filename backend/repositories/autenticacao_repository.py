from sqlalchemy import delete, func, select
from app.extensions import db
from models import AuthSession, LoginAttempt


class AutenticacaoRepository:
    """Bulk operations on login sessions and on the failed-login counter."""

    @staticmethod
    def remover_sessoes_expiradas(agora):
        db.session.execute(delete(AuthSession).where(AuthSession.expires_at < agora))

    @staticmethod
    def remover_sessoes_do_usuario(usuario_id):
        db.session.execute(delete(AuthSession).where(AuthSession.usuario_id == usuario_id))

    @staticmethod
    def remover_tentativas_anteriores(limite):
        db.session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < limite))

    @staticmethod
    def contar_tentativas(chave):
        return db.session.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.key == chave))

    @staticmethod
    def remover_tentativas(chave):
        db.session.execute(delete(LoginAttempt).where(LoginAttempt.key == chave))
