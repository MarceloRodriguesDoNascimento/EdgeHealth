# Caso de uso: listar dispositivos
from werkzeug.exceptions import BadRequest
from repositories import DispositivoRepository
from services.comum.serializador import Serializador


# Lista de dispositivos
class ListarDispositivosService:
    # Devolve os dispositivos, com ou sem arquivados
    def executar(self, empresa_id, arquivados='0'):
        if arquivados not in ('0', '1'): raise BadRequest('arquivados deve ser 0 ou 1.')
        return [Serializador.dispositivo(d) for d in DispositivoRepository.listar_da_empresa(empresa_id, arquivados == '1')]
