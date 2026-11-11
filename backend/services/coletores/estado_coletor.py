# Calcula a situação do coletor
from flask import current_app
from models import utcnow


# Situação do coletor
class EstadoColetor:
    # Diz se está ativo, desatualizado, revogado ou nunca conectou
    @staticmethod
    def calcular(coletor, agora=None):
        if coletor.revogado_em:
            return 'REVOGADO'
        if not coletor.ultimo_contato:
            return 'NUNCA_CONECTADO'
        age = ((agora or utcnow()) - coletor.ultimo_contato).total_seconds()
        return 'DESATUALIZADO' if age > current_app.config['COLLECTOR_STALE_SECONDS'] else 'ATIVO'
