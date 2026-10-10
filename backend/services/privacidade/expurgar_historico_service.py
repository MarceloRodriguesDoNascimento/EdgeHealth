from datetime import timedelta
from models import utcnow
from repositories import RetencaoRepository, Transacao


class ExpurgarHistoricoService:
    """Removes raw samples older than the retention period and expired security records.

    Incidents, impacts and diagnoses are kept: diagnoses already store the values of
    the samples they cite, so the explanation survives the purge of raw samples.
    """

    def executar(self, dias, simular=False):
        now = utcnow()
        cutoff = now - timedelta(days=dias)
        result = dict(limite=cutoff.isoformat() + 'Z', simulacao=simular)
        result.update(RetencaoRepository.expurgar(cutoff, now, simular))
        Transacao.confirmar()
        return result
