from werkzeug.exceptions import NotFound
from repositories import MetricaRepository
from services.comum.serializador import Serializador


class ObterMetricaService:
    def executar(self, empresa_id, id):
        m = MetricaRepository.buscar_da_empresa(empresa_id, id)
        if not m: raise NotFound('Métrica não encontrada.')
        return Serializador.metrica(m)
