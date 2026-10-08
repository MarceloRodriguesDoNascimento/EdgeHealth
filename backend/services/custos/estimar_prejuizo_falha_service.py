from models import Dispositivo, Empresa
from .calculadora_prejuizo import CalculadoraPrejuizo
from .identificar_grupo_compartilhado_service import IdentificarGrupoCompartilhadoService


class EstimarPrejuizoFalhaService:
    """Estimate of one incident plus, for a shared outage, the de-duplicated group total."""

    def executar(self, falha, agora=None):
        empresa = Empresa.buscar_por_id(Dispositivo.buscar_por_id(falha.dispositivo_id).empresa_id)
        result = CalculadoraPrejuizo.estimar(falha, empresa, agora)
        if result['configurado']:
            members = IdentificarGrupoCompartilhadoService().executar(falha)
            result['grupo'] = CalculadoraPrejuizo.estimar_grupo(members, empresa, agora) if len(members) > 1 else None
        return result
