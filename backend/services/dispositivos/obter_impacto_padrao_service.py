# Caso de uso: sugerir impacto pelo tipo do dispositivo
from models import Empresa
from services.custos.categoria_dispositivo import CategoriaDispositivo


# Sugestão de impacto
class ObterImpactoPadraoService:
    # Devolve pessoas e % de perda sugeridos
    def executar(self, empresa_id, tipo):
        return CategoriaDispositivo.padroes(tipo, Empresa.buscar_por_id(empresa_id))
