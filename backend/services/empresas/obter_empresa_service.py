from models import Empresa
from services.comum.serializador import Serializador


class ObterEmpresaService:
    def executar(self, empresa_id):
        return Serializador.empresa(Empresa.buscar_por_id(empresa_id))
