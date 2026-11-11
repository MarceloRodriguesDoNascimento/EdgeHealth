# Controller dos dados e custos da empresa
from services.empresas.atualizar_empresa_service import AtualizarEmpresaService
from services.empresas.configurar_custos_service import ConfigurarCustosService
from services.empresas.obter_empresa_service import ObterEmpresaService
from services.empresas.pular_assistente_custos_service import PularAssistenteCustosService
from services.empresas.simular_custo_hora_service import SimularCustoHoraService
from .base_controller import BaseController


# Rotas da empresa
class EmpresaController(BaseController):
    # GET /api/empresa: dados da empresa e resumo dos custos
    def obter(self):
        return self.resposta(ObterEmpresaService().executar(self.empresa_id()))

    # PUT /api/empresa: altera nome, CNPJ, e-mail e telefone
    def atualizar(self):
        dados = self.payload(['nome_fantasia', 'cnpj', 'email', 'telefone'])
        return self.resposta(AtualizarEmpresaService().executar(self.empresa_id(), dados))

    # PUT /api/empresa/custos: salva os custos e o expediente
    def configurar_custos(self):
        dados = self.payload(['salario_medio', 'fator_encargos', 'horas_mes', 'total_funcionarios', 'expediente', 'fuso'])
        return self.resposta(ConfigurarCustosService().executar(self.empresa_id(), dados))

    # POST /api/empresa/custos/previa: prévia do custo/hora sem salvar
    def simular_custos(self):
        dados = self.payload(['salario_medio', 'fator_encargos', 'horas_mes'])
        return self.resposta(SimularCustoHoraService().executar(dados))

    # POST /api/empresa/custos/pular: não mostra mais o assistente
    def pular_assistente_custos(self):
        self.payload([])
        return self.resposta(PularAssistenteCustosService().executar(self.empresa_id()))
