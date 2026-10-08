from datetime import timedelta
from sqlalchemy import delete, func, select
from app.extensions import db
from models import AuthSession, LoginAttempt, Metrica


class RetencaoRepository:
    """Retention policy: raw samples and expired security records."""

    @staticmethod
    def expurgar(corte, agora, simular):
        """{table: rows older than the limit}; rows are deleted unless `simular`."""
        alvos = [(Metrica, Metrica.coletada_em < corte),
                 (AuthSession, AuthSession.expires_at < agora),
                 (LoginAttempt, LoginAttempt.created_at < agora - timedelta(days=1))]
        resultado = {}
        for model, condicao in alvos:
            resultado[model.__tablename__] = db.session.scalar(select(func.count()).select_from(model).where(condicao))
            if not simular:
                db.session.execute(delete(model).where(condicao))
        return resultado
