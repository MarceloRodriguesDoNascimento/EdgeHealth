from sqlalchemy import text
from app.extensions import db


class DashboardRepository:
    """Dashboard aggregations written in SQL (GROUP BY executed by the database)."""

    STATUS_SQL = text("""
        SELECT COALESCE(status, 'SEM_COLETA') AS status, COUNT(*) AS total
        FROM dispositivos
        WHERE empresa_id = :empresa_id AND arquivado_em IS NULL
        GROUP BY COALESCE(status, 'SEM_COLETA')
    """)

    SEVERIDADE_SQL = text("""
        SELECT f.severidade AS severidade, COUNT(*) AS total
        FROM falhas f
        JOIN dispositivos d ON d.id = f.dispositivo_id
        WHERE d.empresa_id = :empresa_id AND f.estado = 'ABERTA'
        GROUP BY f.severidade
    """)

    @classmethod
    def contagem_por_status(cls, empresa_id):
        """{status: devices} of the active devices; SEM_COLETA = never measured."""
        return {linha.status: linha.total for linha in db.session.execute(cls.STATUS_SQL, {'empresa_id': empresa_id})}

    @classmethod
    def contagem_por_severidade(cls, empresa_id):
        """{severity: open incidents} of the company."""
        return {linha.severidade: linha.total
                for linha in db.session.execute(cls.SEVERIDADE_SQL, {'empresa_id': empresa_id})}
