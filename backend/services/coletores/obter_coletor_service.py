from werkzeug.exceptions import NotFound
from repositories import ColetorRepository


class ObterColetorService:
    """Collector of the company or 404 (never reveals collectors of other companies)."""

    def executar(self, empresa_id, id):
        coletor = ColetorRepository.buscar_da_empresa(empresa_id, id)
        if not coletor:
            raise NotFound('Coletor não encontrado.')
        return coletor
