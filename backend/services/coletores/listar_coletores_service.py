from repositories import ColetorRepository
from services.comum.serializador import Serializador


class ListarColetoresService:
    """Read-only for every member (needed to assign devices); management is admin-only."""

    def executar(self, empresa_id):
        return [Serializador.coletor(c) for c in ColetorRepository.listar_da_empresa(empresa_id)]
