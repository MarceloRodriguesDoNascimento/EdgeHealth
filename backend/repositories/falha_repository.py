from sqlalchemy import select
from app.extensions import db
from models import Dispositivo, Falha
from .paginacao import filtrar_periodo, paginar


class FalhaRepository:
    """Incident queries: tenant scope, filtered history, correlation windows and shared outages."""

    @staticmethod
    def _da_empresa(empresa_id):
        return select(Falha).join(Dispositivo).where(Dispositivo.empresa_id == empresa_id)

    @classmethod
    def buscar_da_empresa(cls, empresa_id, id):
        return db.session.scalar(cls._da_empresa(empresa_id).where(Falha.id == id))

    @staticmethod
    def aberta_do_dispositivo(dispositivo_id):
        return db.session.scalar(select(Falha).where(Falha.dispositivo_id == dispositivo_id, Falha.estado == 'ABERTA'))

    @classmethod
    def historico(cls, empresa_id, dispositivo_id, severidade, estado, inicio, fim, pagina, limite):
        """Filtered, newest first and paginated history: (rows, total)."""
        query = cls._da_empresa(empresa_id)
        if dispositivo_id:
            query = query.where(Falha.dispositivo_id == dispositivo_id)
        if severidade:
            query = query.where(Falha.severidade == severidade)
        if estado:
            query = query.where(Falha.estado == estado)
        query = filtrar_periodo(query, Falha.inicio, inicio, fim)
        return paginar(query.order_by(Falha.inicio.desc(), Falha.id.desc()), pagina, limite)

    @classmethod
    def abertas_da_empresa(cls, empresa_id):
        return db.session.scalars(cls._da_empresa(empresa_id).where(Falha.estado == 'ABERTA')).all()

    @classmethod
    def encerradas_desde(cls, empresa_id, desde):
        return db.session.scalars(cls._da_empresa(empresa_id).where(Falha.estado == 'ENCERRADA',
                                                                    Falha.inicio >= desde)).all()

    @classmethod
    def recentes_da_empresa(cls, empresa_id, limite=8):
        return db.session.scalars(cls._da_empresa(empresa_id).order_by(Falha.inicio.desc(), Falha.id.desc())
                                  .limit(limite)).all()

    @classmethod
    def iniciadas_desde(cls, empresa_id, desde):
        return db.session.scalars(cls._da_empresa(empresa_id).where(Falha.inicio >= desde).order_by(Falha.inicio)).all()

    @staticmethod
    def ids_anteriores_do_dispositivo(dispositivo_id, exceto_id, desde, ate, limite=20):
        return list(db.session.scalars(select(Falha.id).where(
            Falha.dispositivo_id == dispositivo_id, Falha.id != exceto_id, Falha.inicio >= desde,
            Falha.inicio <= ate).order_by(Falha.inicio.desc()).limit(limite)))

    @classmethod
    def grupo_compartilhado(cls, empresa_id, inicio_de, inicio_ate):
        """Unavailability incidents of the company that started inside the correlation window."""
        return db.session.scalars(cls._da_empresa(empresa_id).where(
            Falha.tipo == 'INDISPONIBILIDADE', Falha.inicio >= inicio_de, Falha.inicio <= inicio_ate)
            .order_by(Falha.id)).all()
