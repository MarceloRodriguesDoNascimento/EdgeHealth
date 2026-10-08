from werkzeug.exceptions import NotFound
from repositories import FalhaRepository
from services.comum.serializador import Serializador


class ObterFalhaService:
    """Incident of the company (with diagnosis and loss estimate) or 404."""

    def buscar(self, empresa_id, id):
        f = FalhaRepository.buscar_da_empresa(empresa_id, id)
        if not f:
            raise NotFound('Ocorrência não encontrada.')
        return f

    def executar(self, empresa_id, id):
        return Serializador.falha(self.buscar(empresa_id, id), True)
