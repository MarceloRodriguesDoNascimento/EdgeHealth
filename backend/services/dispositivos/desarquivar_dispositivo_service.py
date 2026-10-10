from werkzeug.exceptions import Conflict
from models import utcnow
from repositories import DispositivoRepository
from services.comum.serializador import Serializador
from .obter_dispositivo_service import ObterDispositivoService


class DesarquivarDispositivoService:
    def executar(self, empresa_id, id):
        device = ObterDispositivoService().buscar(empresa_id, id)
        if not device.arquivado_em:
            raise Conflict('O dispositivo não está arquivado.')
        if DispositivoRepository.existe_ip_ativo(device.empresa_id, device.ip):
            raise Conflict('Já existe um dispositivo ativo com este IP. Arquive-o ou altere o IP antes de desarquivar.')
        device.arquivado_em = None
        # History is preserved; the current state restarts from a fresh measurement instead of showing stale data.
        device.reiniciar_estado()
        device.atualizar(erro_coleta=None, lease_owner=None, lease_until=None, proxima_coleta=utcnow())
        return Serializador.dispositivo(device)
