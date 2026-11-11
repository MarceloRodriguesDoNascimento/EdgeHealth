# Caso de uso: listar coletores
from repositories import ColetorRepository
from services.comum.serializador import Serializador


# Lista de coletores
class ListarColetoresService:
    # Devolve os coletores da empresa
    def executar(self, empresa_id):
        return [Serializador.coletor(c) for c in ColetorRepository.listar_da_empresa(empresa_id)]
