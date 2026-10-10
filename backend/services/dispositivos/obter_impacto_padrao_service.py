from models import Empresa
from services.custos.categoria_dispositivo import CategoriaDispositivo


class ObterImpactoPadraoService:
    """Suggested business impact for a device type, shown while filling the form."""

    def executar(self, empresa_id, tipo):
        return CategoriaDispositivo.padroes(tipo, Empresa.buscar_por_id(empresa_id))
