from datetime import timedelta
from models import Empresa
from repositories import FalhaRepository
from .calcular_prejuizo_total_service import CalcularPrejuizoTotalService


class ResumirPrejuizoService:
    """Estimated loss of the incidents started in the last `dias` days (shared outages de-duplicated)."""

    def executar(self, empresa_id, agora, dias=30):
        failures = FalhaRepository.iniciadas_desde(empresa_id, agora - timedelta(days=dias))
        result = CalcularPrejuizoTotalService().executar(failures, Empresa.buscar_por_id(empresa_id), agora)
        result.pop('individual', None)
        return dict(result, dias=dias)
