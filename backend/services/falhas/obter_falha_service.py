# Caso de uso: buscar uma ocorrência
from werkzeug.exceptions import NotFound
from repositories import FalhaRepository
from services.comum.serializador import Serializador


# Busca de ocorrência
class ObterFalhaService:
    # Busca a falha ou responde 404
    def buscar(self, empresa_id, id):
        f = FalhaRepository.buscar_da_empresa(empresa_id, id)
        if not f:
            raise NotFound('Ocorrência não encontrada.')
        return f

    # Devolve a falha com diagnóstico e prejuízo
    def executar(self, empresa_id, id):
        return Serializador.falha(self.buscar(empresa_id, id), True)
