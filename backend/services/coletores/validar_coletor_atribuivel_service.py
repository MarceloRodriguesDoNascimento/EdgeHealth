from werkzeug.exceptions import Conflict
from app import validation as v
from .obter_coletor_service import ObterColetorService


class ValidarColetorAtribuivelService:
    """Validates a coletor_id sent with a device form: same company and not revoked."""

    def executar(self, empresa_id, valor):
        if valor is None:
            return None
        coletor = ObterColetorService().executar(empresa_id, v.integer(valor, 'Coletor', 1, 2147483647))
        if coletor.revogado_em:
            raise Conflict('O coletor está revogado.')
        return coletor.id
