# Gera a credencial do coletor (ehc_...)
import secrets
from services.comum.hash_token import HashToken


# Geração de credencial
class CredencialColetor:
    PREFIXO = 'ehc_'

    # Cria token, hash e prefixo
    @classmethod
    def gerar(cls):
        token = cls.PREFIXO + secrets.token_urlsafe(32)
        return token, HashToken.sha256(token), token[:12]
