# Caso de uso: buscar um coletor
from werkzeug.exceptions import NotFound
from repositories import ColetorRepository


# Busca de coletor
class ObterColetorService:
    # Devolve o coletor ou 404
    def executar(self, empresa_id, id):
        coletor = ColetorRepository.buscar_da_empresa(empresa_id, id)
        if not coletor:
            raise NotFound('Coletor não encontrado.')
        return coletor
