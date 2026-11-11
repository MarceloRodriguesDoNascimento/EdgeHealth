# Controller que diz se o servidor está no ar
from services.saude.verificar_saude_service import VerificarSaudeService
from .base_controller import BaseController


# Rota de saúde
class HealthController(BaseController):
    # GET /api/health: 200 se pronto, 503 se indisponível
    def verificar(self):
        corpo, pronto = VerificarSaudeService().executar()
        return self.resposta(corpo, 200 if pronto else 503)
