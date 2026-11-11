# Confere o coletor escolhido no formulário do dispositivo
from werkzeug.exceptions import Conflict
from app import validation as v
from .obter_coletor_service import ObterColetorService


# Validação de coletor
class ValidarColetorAtribuivelService:
    # Confere se o coletor existe e está ativo
    def executar(self, empresa_id, valor):
        if valor is None:
            return None
        coletor = ObterColetorService().executar(empresa_id, v.integer(valor, 'Coletor', 1, 2147483647))
        if coletor.revogado_em:
            raise Conflict('O coletor está revogado.')
        return coletor.id
