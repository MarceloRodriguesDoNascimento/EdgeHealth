import logging
from app import validation as v
from models import Coletor
from services.comum.serializador import Serializador
from .credencial_coletor import CredencialColetor

log = logging.getLogger(__name__)


class CadastrarColetorService:
    def executar(self, empresa_id, nome):
        token, token_hash, prefix = CredencialColetor.gerar()
        c = Coletor(empresa_id=empresa_id, nome=v.string(nome, 'Nome', 100), token_hash=token_hash, token_prefixo=prefix).salvar()
        log.info('Coletor criado empresa=%s coletor=%s prefixo=%s', c.empresa_id, c.id, prefix)
        # The plain credential is returned only once and never stored.
        return dict(coletor=Serializador.coletor(c), token=token)
