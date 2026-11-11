# Caso de uso: arquivar dispositivo
from werkzeug.exceptions import Conflict
from models import utcnow
from repositories import FalhaRepository, Transacao
from services.diagnosticos.atualizar_diagnosticos_service import AtualizarDiagnosticosService
from .obter_dispositivo_service import ObterDispositivoService


# Arquivamento
class ArquivarDispositivoService:
    # Para de monitorar e encerra a falha aberta
    def executar(self, empresa_id, id):
        device = ObterDispositivoService().buscar(empresa_id, id, incluir_arquivados=False)
        if device.em_coleta(utcnow()):
            raise Conflict('Há uma coleta em andamento. Aguarde sua conclusão para arquivar.')
        now = utcnow()
        device.arquivado_em = now
        current = FalhaRepository.aberta_do_dispositivo(id)
        if current:
            current.encerrar(now, 'ARQUIVAMENTO')
            AtualizarDiagnosticosService().executar(device.empresa_id, now, falha_extra=current)
        Transacao.confirmar()
