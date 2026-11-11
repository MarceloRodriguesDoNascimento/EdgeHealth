# Caso de uso: prejuízo de uma falha
from models import Dispositivo, Empresa
from .calculadora_prejuizo import CalculadoraPrejuizo
from .identificar_grupo_compartilhado_service import IdentificarGrupoCompartilhadoService


# Estimativa de uma falha
class EstimarPrejuizoFalhaService:
    # Calcula o prejuízo e, se houver, o do grupo
    def executar(self, falha, agora=None):
        empresa = Empresa.buscar_por_id(Dispositivo.buscar_por_id(falha.dispositivo_id).empresa_id)
        result = CalculadoraPrejuizo.estimar(falha, empresa, agora)
        if result['configurado']:
            members = IdentificarGrupoCompartilhadoService().executar(falha)
            result['grupo'] = CalculadoraPrejuizo.estimar_grupo(members, empresa, agora) if len(members) > 1 else None
        return result
