import secrets
from services.comum.hash_token import HashToken


class CredencialColetor:
    """Bearer credential of a collector: shown once, stored only as SHA-256 plus a display prefix."""

    PREFIXO = 'ehc_'

    @classmethod
    def gerar(cls):
        """(plain token, hash to store, prefix to display)."""
        token = cls.PREFIXO + secrets.token_urlsafe(32)
        return token, HashToken.sha256(token), token[:12]
