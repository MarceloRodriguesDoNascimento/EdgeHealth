# Caso de uso: pular o assistente de custos
from models import Empresa
from services.comum.serializador import Serializador


# Pular assistente
class PularAssistenteCustosService:
    # Marca que o assistente foi dispensado
    def executar(self, empresa_id):
        company = Empresa.buscar_por_id(empresa_id)
        if company.assistente_custos is None:
            company.atualizar(assistente_custos='PULADO')
        return Serializador.empresa(company)
