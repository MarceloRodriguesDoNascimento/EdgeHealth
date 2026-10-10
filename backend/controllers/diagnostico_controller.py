from services.diagnosticos.listar_recomendacoes_service import ListarRecomendacoesService
from services.diagnosticos.obter_diagnostico_service import ObterDiagnosticoService
from .base_controller import BaseController


class DiagnosticoController(BaseController):
    """Diagnoses and the corrective-action catalog (Recomendacao)."""

    def obter(self, id):
        return self.resposta(ObterDiagnosticoService().executar(self.empresa_id(), id))

    def listar_recomendacoes(self):
        return self.resposta(ListarRecomendacoesService().executar())
