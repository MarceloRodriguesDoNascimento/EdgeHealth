# Consultas de sessões e tentativas de login
from sqlalchemy import delete, func, select
from app.extensions import db
from models import AuthSession, LoginAttempt


# Operações em lote de sessões e tentativas
class AutenticacaoRepository:
    # Apaga as sessões vencidas
    @staticmethod
    def remover_sessoes_expiradas(agora):
        db.session.execute(delete(AuthSession).where(AuthSession.expires_at < agora))

    # Encerra todas as sessões de um usuário
    @staticmethod
    def remover_sessoes_do_usuario(usuario_id):
        db.session.execute(delete(AuthSession).where(AuthSession.usuario_id == usuario_id))

    # Apaga tentativas de login antigas
    @staticmethod
    def remover_tentativas_anteriores(limite):
        db.session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < limite))

    # Conta as tentativas erradas recentes
    @staticmethod
    def contar_tentativas(chave):
        return db.session.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.key == chave))

    # Apaga as tentativas de uma chave após login certo
    @staticmethod
    def remover_tentativas(chave):
        db.session.execute(delete(LoginAttempt).where(LoginAttempt.key == chave))
