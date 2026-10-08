from werkzeug.exceptions import NotFound
from repositories import DispositivoRepository
from services.comum.serializador import Serializador


class ObterDispositivoService:
    """Device of the company or 404 (never reveals devices of other companies)."""

    def buscar(self, empresa_id, id, incluir_arquivados=True):
        device = DispositivoRepository.buscar_da_empresa(empresa_id, id, incluir_arquivados)
        if not device:
            raise NotFound('Dispositivo não encontrado.')
        return device

    def executar(self, empresa_id, id):
        return Serializador.dispositivo(self.buscar(empresa_id, id))
