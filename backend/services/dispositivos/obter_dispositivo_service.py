# Caso de uso: buscar um dispositivo
from werkzeug.exceptions import NotFound
from repositories import DispositivoRepository
from services.comum.serializador import Serializador


# Busca de dispositivo
class ObterDispositivoService:
    # Busca o dispositivo ou responde 404
    def buscar(self, empresa_id, id, incluir_arquivados=True):
        device = DispositivoRepository.buscar_da_empresa(empresa_id, id, incluir_arquivados)
        if not device:
            raise NotFound('Dispositivo não encontrado.')
        return device

    # Devolve o dispositivo em JSON
    def executar(self, empresa_id, id):
        return Serializador.dispositivo(self.buscar(empresa_id, id))
