# Controller das medições gravadas
from services.metricas.listar_metricas_service import ListarMetricasService
from services.metricas.obter_metrica_service import ObterMetricaService
from .base_controller import BaseController


# Rotas de métricas
class MetricaController(BaseController):
    # GET /api/metricas: medições paginadas por período
    def listar(self):
        return self.resposta(ListarMetricasService().executar(
            self.empresa_id(), dispositivo_id=self.parametro('dispositivo_id'), tipo=self.parametro('tipo'),
            inicio=self.parametro('inicio'), fim=self.parametro('fim'),
            pagina=self.parametro('pagina'), limite=self.parametro('limite')))

    # GET /api/metricas/<id>: uma medição
    def obter(self, id):
        return self.resposta(ObterMetricaService().executar(self.empresa_id(), id))
