from repositories import DiagnosticoRepository
from services.comum.serializador import Serializador


class ListarRecomendacoesService:
    """Corrective-action catalog, grouped by rule."""

    def executar(self):
        return [Serializador.recomendacao(r) for r in DiagnosticoRepository.catalogo()]
