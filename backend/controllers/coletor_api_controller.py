# Controller das rotas usadas pelo programa coletor
from flask import g
from services.coletor_api.obter_configuracao_coletor_service import ObterConfiguracaoColetorService
from services.coletor_api.receber_amostras_service import ReceberAmostrasService
from services.coletor_api.registrar_heartbeat_service import RegistrarHeartbeatService
from .base_controller import BaseController


# Rotas do protocolo do coletor remoto
class ColetorApiController(BaseController):
    # Coletor autenticado nesta requisição
    @staticmethod
    def coletor():
        return g.collector

    # GET /api/coletor/configuracao: o que o coletor deve medir
    def configuracao(self):
        return self.resposta(ObterConfiguracaoColetorService().executar(self.coletor()))

    # POST /api/coletor/heartbeat: sinal de vida do coletor
    def heartbeat(self):
        dados = self.payload(['versao', 'fila_pendente', 'erro'])
        return self.resposta(RegistrarHeartbeatService().executar(self.coletor(), dados))

    # POST /api/coletor/amostras: recebe o lote de medições
    def amostras(self):
        dados = self.payload(['amostras', 'erros'])
        return self.resposta(ReceberAmostrasService().executar(self.coletor(), dados))
