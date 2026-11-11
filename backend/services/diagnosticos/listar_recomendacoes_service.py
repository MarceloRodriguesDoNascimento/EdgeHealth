# Caso de uso: listar o catálogo de recomendações
from repositories import DiagnosticoRepository
from services.comum.serializador import Serializador


# Lista de recomendações
class ListarRecomendacoesService:
    # Devolve o catálogo agrupado por regra
    def executar(self):
        return [Serializador.recomendacao(r) for r in DiagnosticoRepository.catalogo()]
