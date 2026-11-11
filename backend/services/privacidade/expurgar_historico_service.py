# Caso de uso: apagar histórico antigo (LGPD)
from datetime import timedelta
from models import utcnow
from repositories import RetencaoRepository, Transacao


# Expurgo de histórico
class ExpurgarHistoricoService:
    # Apaga medições e registros vencidos
    def executar(self, dias, simular=False):
        now = utcnow()
        cutoff = now - timedelta(days=dias)
        result = dict(limite=cutoff.isoformat() + 'Z', simulacao=simular)
        result.update(RetencaoRepository.expurgar(cutoff, now, simular))
        Transacao.confirmar()
        return result
