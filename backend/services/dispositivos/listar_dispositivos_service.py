from werkzeug.exceptions import BadRequest
from repositories import DispositivoRepository
from services.comum.serializador import Serializador


class ListarDispositivosService:
    def executar(self, empresa_id, arquivados='0'):
        """arquivados: '0' only active devices, '1' also the archived ones."""
        if arquivados not in ('0', '1'): raise BadRequest('arquivados deve ser 0 ou 1.')
        return [Serializador.dispositivo(d) for d in DispositivoRepository.listar_da_empresa(empresa_id, arquivados == '1')]
