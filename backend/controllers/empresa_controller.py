from services.empresas.atualizar_empresa_service import AtualizarEmpresaService
from services.empresas.configurar_custos_service import ConfigurarCustosService
from services.empresas.obter_empresa_service import ObterEmpresaService
from services.empresas.pular_assistente_custos_service import PularAssistenteCustosService
from .base_controller import BaseController


class EmpresaController(BaseController):
    def obter(self):
        return self.resposta(ObterEmpresaService().executar(self.empresa_id()))

    def atualizar(self):
        dados = self.payload(['nome_fantasia', 'cnpj', 'email', 'telefone'])
        return self.resposta(AtualizarEmpresaService().executar(self.empresa_id(), dados))

    def configurar_custos(self):
        dados = self.payload(['salario_medio', 'fator_encargos', 'horas_mes', 'total_funcionarios', 'expediente', 'fuso'])
        return self.resposta(ConfigurarCustosService().executar(self.empresa_id(), dados))

    def pular_assistente_custos(self):
        self.payload([])
        return self.resposta(PularAssistenteCustosService().executar(self.empresa_id()))
