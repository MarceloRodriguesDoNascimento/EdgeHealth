import logging
from werkzeug.exceptions import Conflict
from models import utcnow
from services.comum.serializador import Serializador
from .credencial_coletor import CredencialColetor
from .obter_coletor_service import ObterColetorService

log = logging.getLogger(__name__)


class RotacionarCredencialColetorService:
    """New credential for the collector; the previous one stops working immediately."""

    def executar(self, empresa_id, id):
        c = ObterColetorService().executar(empresa_id, id)
        if c.revogado_em:
            raise Conflict('Coletor revogado não pode receber nova credencial. Cadastre outro coletor.')
        token, token_hash, prefix = CredencialColetor.gerar()
        c.atualizar(token_hash=token_hash, token_prefixo=prefix, rotacionado_em=utcnow())
        log.info('Credencial rotacionada coletor=%s prefixo=%s', c.id, c.token_prefixo)
        return dict(coletor=Serializador.coletor(c), token=token)
