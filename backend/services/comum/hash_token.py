# Transforma credenciais em SHA-256 antes de guardar
import hashlib


# Hash de credenciais
class HashToken:
    # Calcula o SHA-256 do texto
    @staticmethod
    def sha256(valor):
        return hashlib.sha256(valor.encode()).hexdigest()
