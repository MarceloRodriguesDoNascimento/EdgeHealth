from services.falhas.explicar_falha_com_ia_service import ExplicarFalhaComIaService
from services.falhas.listar_falhas_service import ListarFalhasService
from services.falhas.obter_falha_service import ObterFalhaService
from services.falhas.registrar_impacto_service import RegistrarImpactoService
from .base_controller import BaseController


class FalhaController(BaseController):
    def listar(self):
        return self.resposta(ListarFalhasService().executar(
            self.empresa_id(), dispositivo_id=self.parametro('dispositivo_id'),
            severidade=self.parametro('severidade'), estado=self.parametro('estado'),
            inicio=self.parametro('inicio'), fim=self.parametro('fim'),
            pagina=self.parametro('pagina'), limite=self.parametro('limite')))

    def obter(self, id):
        return self.resposta(ObterFalhaService().executar(self.empresa_id(), id))

    def registrar_impacto(self, id):
        falha = ObterFalhaService().buscar(self.empresa_id(), id)  # 404 comes before payload errors
        dados = self.payload(['usuarios_afetados', 'observacao', 'custos_diretos'])
        return self.resposta(RegistrarImpactoService().executar(self.empresa_id(), falha, dados))

    def explicar_com_ia(self, id):
        falha = ObterFalhaService().buscar(self.empresa_id(), id)  # 404 for another company's incident
        self.payload([])
        return self.resposta(ExplicarFalhaComIaService().executar(self.empresa_id(), falha))
