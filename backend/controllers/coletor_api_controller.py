from flask import g
from services.coletor_api.obter_configuracao_coletor_service import ObterConfiguracaoColetorService
from services.coletor_api.receber_amostras_service import ReceberAmostrasService
from services.coletor_api.registrar_heartbeat_service import RegistrarHeartbeatService
from .base_controller import BaseController


class ColetorApiController(BaseController):
    """Protocol used by the remote collector (bearer credential, see app.security.require_collector)."""

    @staticmethod
    def coletor():
        return g.collector

    def configuracao(self):
        return self.resposta(ObterConfiguracaoColetorService().executar(self.coletor()))

    def heartbeat(self):
        dados = self.payload(['versao', 'fila_pendente', 'erro'])
        return self.resposta(RegistrarHeartbeatService().executar(self.coletor(), dados))

    def amostras(self):
        dados = self.payload(['amostras', 'erros'])
        return self.resposta(ReceberAmostrasService().executar(self.coletor(), dados))
