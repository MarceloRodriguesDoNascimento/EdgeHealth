# Controller de diagnósticos e recomendações
from services.diagnosticos.listar_recomendacoes_service import ListarRecomendacoesService
from services.diagnosticos.obter_diagnostico_service import ObterDiagnosticoService
from .base_controller import BaseController


# Rotas de diagnóstico
class DiagnosticoController(BaseController):
    # GET /api/diagnosticos/<id>: causas, evidências e recomendações
    def obter(self, id):
        return self.resposta(ObterDiagnosticoService().executar(self.empresa_id(), id))

    # GET /api/recomendacoes: catálogo de ações corretivas
    def listar_recomendacoes(self):
        return self.resposta(ListarRecomendacoesService().executar())
