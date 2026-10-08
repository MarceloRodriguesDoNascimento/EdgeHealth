import hashlib


class HashToken:
    """Credentials (session, CSRF, collector) are stored only as their SHA-256."""

    @staticmethod
    def sha256(valor):
        return hashlib.sha256(valor.encode()).hexdigest()
