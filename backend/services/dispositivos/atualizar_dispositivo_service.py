# Caso de uso: editar dispositivo
from werkzeug.exceptions import Conflict
from models import utcnow
from repositories import FalhaRepository
from services.comum.serializador import Serializador
from .dados_dispositivo import DadosDispositivo
from .obter_dispositivo_service import ObterDispositivoService


# Edição de dispositivo
class AtualizarDispositivoService:
    # Valida e grava as alterações
    def executar(self, empresa_id, id, dados):
        device = ObterDispositivoService().buscar(empresa_id, id, incluir_arquivados=False)
        if device.em_coleta(utcnow()):
            raise Conflict('Há uma coleta em andamento. Aguarde sua conclusão para editar.')
        old_ip = device.ip
        DadosDispositivo.aplicar(device, dados, empresa_id, criando=False)
        if old_ip != device.ip:
            if FalhaRepository.aberta_do_dispositivo(id):
                raise Conflict('Encerre a ocorrência por recuperação ou arquive o dispositivo antes de alterar o IP.')
            device.reiniciar_estado()
            device.proxima_coleta = utcnow()
        device.atualizar()
        return Serializador.dispositivo(device)
