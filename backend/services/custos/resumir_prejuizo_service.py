# Caso de uso: prejuízo dos últimos 30 dias para o painel
from datetime import timedelta
from models import Empresa
from repositories import FalhaRepository
from .calcular_prejuizo_total_service import CalcularPrejuizoTotalService


# Resumo de prejuízo
class ResumirPrejuizoService:
    # Soma o prejuízo do período
    def executar(self, empresa_id, agora, dias=30):
        failures = FalhaRepository.iniciadas_desde(empresa_id, agora - timedelta(days=dias))
        result = CalcularPrejuizoTotalService().executar(failures, Empresa.buscar_por_id(empresa_id), agora)
        result.pop('individual', None)
        return dict(result, dias=dias)
