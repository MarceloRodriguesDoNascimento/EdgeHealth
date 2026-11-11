# Caso de uso: dados da empresa
from models import Empresa
from services.comum.serializador import Serializador


# Busca da empresa
class ObterEmpresaService:
    # Devolve a empresa em JSON
    def executar(self, empresa_id):
        return Serializador.empresa(Empresa.buscar_por_id(empresa_id))
