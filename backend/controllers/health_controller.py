from services.saude.verificar_saude_service import VerificarSaudeService
from .base_controller import BaseController


class HealthController(BaseController):
    def verificar(self):
        corpo, pronto = VerificarSaudeService().executar()
        return self.resposta(corpo, 200 if pronto else 503)
