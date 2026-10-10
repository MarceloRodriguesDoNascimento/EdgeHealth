from flask import current_app
from models import utcnow


class EstadoColetor:
    """REVOGADO, NUNCA_CONECTADO, DESATUALIZADO (no recent contact) or ATIVO."""

    @staticmethod
    def calcular(coletor, agora=None):
        if coletor.revogado_em:
            return 'REVOGADO'
        if not coletor.ultimo_contato:
            return 'NUNCA_CONECTADO'
        age = ((agora or utcnow()) - coletor.ultimo_contato).total_seconds()
        return 'DESATUALIZADO' if age > current_app.config['COLLECTOR_STALE_SECONDS'] else 'ATIVO'
