# Contagens do painel em SQL com GROUP BY
from sqlalchemy import text
from app.extensions import db


# Consultas do painel
class DashboardRepository:
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

    # Quantos dispositivos em cada status
    @classmethod
    def contagem_por_status(cls, empresa_id):
        return {linha.status: linha.total for linha in db.session.execute(cls.STATUS_SQL, {'empresa_id': empresa_id})}

    # Quantas falhas abertas em cada severidade
    @classmethod
    def contagem_por_severidade(cls, empresa_id):
        return {linha.severidade: linha.total
                for linha in db.session.execute(cls.SEVERIDADE_SQL, {'empresa_id': empresa_id})}
