# Caso de uso: dizer se o servidor está pronto
from repositories import BancoRepository


# Verificação de saúde
class VerificarSaudeService:
    # Confere o banco e devolve o status
    def executar(self):
        pronto = BancoRepository.esquema_atualizado()
        return dict(status='ok' if pronto else 'migrations_pendentes'), pronto
