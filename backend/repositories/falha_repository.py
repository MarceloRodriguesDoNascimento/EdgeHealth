from sqlalchemy import DateTime, Integer, bindparam, select, text
from app.extensions import db
from models import Dispositivo, Falha
from .paginacao import filtrar_periodo, paginar


class FalhaRepository:
    """Incident queries: tenant scope, filtered history, correlation windows and shared outages."""

    # Incidents per device that overlap [inicio, fim) (NULL bound = open side), most incidents first.
    RANKING_SQL = text("""
        SELECT d.id AS dispositivo_id,
               d.nome AS nome,
               COUNT(f.id) AS falhas,
               SUM(CASE WHEN f.estado = 'ABERTA' THEN 1 ELSE 0 END) AS abertas,
               SUM(CASE WHEN f.tipo = 'INDISPONIBILIDADE' THEN 1 ELSE 0 END) AS indisponibilidades
        FROM falhas f
        JOIN dispositivos d ON d.id = f.dispositivo_id
        WHERE d.empresa_id = :empresa_id
          AND (:dispositivo_id IS NULL OR d.id = :dispositivo_id)
          AND (:inicio IS NULL OR f.fim IS NULL OR f.fim >= :inicio)
          AND (:fim IS NULL OR f.inicio < :fim)
        GROUP BY d.id, d.nome
        ORDER BY falhas DESC, d.id ASC
        LIMIT :limite
    """).bindparams(bindparam('empresa_id', type_=Integer()), bindparam('dispositivo_id', type_=Integer()),
                    bindparam('inicio', type_=DateTime()), bindparam('fim', type_=DateTime()),
                    bindparam('limite', type_=Integer()))

    @classmethod
    def ranking_dispositivos(cls, empresa_id, inicio, fim, limite=5, dispositivo_id=None):
        """[{dispositivo_id, nome, falhas, abertas, indisponibilidades}] of the incidents overlapping the
        period, by number of incidents (ties: lowest device id first)."""
        params = dict(empresa_id=empresa_id, dispositivo_id=dispositivo_id, inicio=inicio, fim=fim, limite=limite)
        return [dict(linha._mapping) for linha in db.session.execute(cls.RANKING_SQL, params)]

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
