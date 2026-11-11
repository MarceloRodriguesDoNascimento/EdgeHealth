# Controller das ocorrências (falhas)
from services.falhas.explicar_falha_com_ia_service import ExplicarFalhaComIaService
from services.falhas.listar_falhas_service import ListarFalhasService
from services.falhas.obter_falha_service import ObterFalhaService
from services.falhas.registrar_impacto_service import RegistrarImpactoService
from .base_controller import BaseController


# Rotas de ocorrências
class FalhaController(BaseController):
    # GET /api/falhas: histórico filtrado e paginado
    def listar(self):
        return self.resposta(ListarFalhasService().executar(
            self.empresa_id(), dispositivo_id=self.parametro('dispositivo_id'),
            severidade=self.parametro('severidade'), estado=self.parametro('estado'),
            inicio=self.parametro('inicio'), fim=self.parametro('fim'),
            pagina=self.parametro('pagina'), limite=self.parametro('limite')))

    # GET /api/falhas/<id>: ocorrência com diagnóstico e prejuízo
    def obter(self, id):
        return self.resposta(ObterFalhaService().executar(self.empresa_id(), id))

    # PUT /api/falhas/<id>/impacto: grava o impacto informado
    def registrar_impacto(self, id):
        return self.resposta(RegistrarImpactoService().executar(self.empresa_id(), id, self.corpo()))

    # POST /api/falhas/<id>/explicacao-ia: explicação gerada pelo Gemini
    def explicar_com_ia(self, id):
        return self.resposta(ExplicarFalhaComIaService().executar(self.empresa_id(), id, self.corpo()))
