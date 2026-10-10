import logging
from datetime import timedelta
from models import Dispositivo, utcnow
from repositories import DispositivoRepository, Transacao
from .registrar_medicao_service import RegistrarMedicaoService
from .reservar_dispositivo_service import ReservarDispositivoService
from .resultado_sonda import CollectorError
from .sonda_icmp_service import SondaIcmpService
from .validar_configuracao_monitor_service import ValidarConfiguracaoMonitorService

log = logging.getLogger(__name__)


class ColetarDispositivoService:
    """Local worker: lease, probe (outside any DB transaction), record and release one device."""

    def executar(self, app, dispositivo_id, sonda=None):
        with app.app_context():
            ValidarConfiguracaoMonitorService().executar(app.config)
            # Devices assigned to a remote collector are never probed by the local worker.
            owner = ReservarDispositivoService().executar(dispositivo_id)
            if not owner:
                return False
            address = Dispositivo.buscar_por_id(dispositivo_id).ip
            Transacao.encerrar()  # Never keep a database transaction open while probing.
            try:
                result = (sonda or SondaIcmpService().executar)(address, app.config['MONITOR_PACKETS'], app.config['MONITOR_TIMEOUT'])
                device = Dispositivo.buscar_por_id(dispositivo_id)
                if device.lease_owner != owner or device.arquivado_em:
                    return False
                RegistrarMedicaoService().executar(device, result)
                device.atualizar(proxima_coleta=utcnow() + timedelta(seconds=app.config['MONITOR_INTERVAL']),
                                 lease_owner=None, lease_until=None)
                log.info('Coleta concluída dispositivo=%s recebidos=%s enviados=%s', dispositivo_id, result.received, result.sent)
                return True
            except Exception as error:
                Transacao.desfazer()
                message = str(error) if isinstance(error, CollectorError) else 'Erro interno na coleta; consulte os logs do worker.'
                log.exception('Coleta não concluída dispositivo=%s', dispositivo_id)
                DispositivoRepository.liberar_reserva(dispositivo_id, owner, erro_coleta=message[:500],
                                                      proxima_coleta=utcnow() + timedelta(seconds=app.config['MONITOR_INTERVAL']))
                Transacao.confirmar()
                return False
            finally:
                Transacao.encerrar()
