from repositories import BancoRepository


class VerificarSaudeService:
    """Ready only when the database answers and its schema is at the latest migration."""

    def executar(self):
        """(response body, ready)."""
        pronto = BancoRepository.esquema_atualizado()
        return dict(status='ok' if pronto else 'migrations_pendentes'), pronto
