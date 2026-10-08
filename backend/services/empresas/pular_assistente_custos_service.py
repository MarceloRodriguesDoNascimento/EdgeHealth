from models import Empresa
from services.comum.serializador import Serializador


class PularAssistenteCustosService:
    """The cost assistant is offered once; skipping keeps the estimate "not configured"."""

    def executar(self, empresa_id):
        company = Empresa.buscar_por_id(empresa_id)
        if company.assistente_custos is None:
            company.atualizar(assistente_custos='PULADO')
        return Serializador.empresa(company)
