# Caso de uso: revogar coletor
import logging
from models import utcnow
from services.comum.serializador import Serializador
from .obter_coletor_service import ObterColetorService

log = logging.getLogger(__name__)


# Revogação de coletor
class RevogarColetorService:
    # Desativa a credencial do coletor
    def executar(self, empresa_id, id):
        c = ObterColetorService().executar(empresa_id, id)
        if not c.revogado_em:
            c.atualizar(revogado_em=utcnow())
            log.info('Coletor revogado coletor=%s', c.id)
        return Serializador.coletor(c)
