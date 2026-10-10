from concurrent.futures import ThreadPoolExecutor
from models import utcnow
from repositories import DispositivoRepository
from .coletar_dispositivo_service import ColetarDispositivoService
from .validar_configuracao_monitor_service import ValidarConfiguracaoMonitorService


class ExecutarCicloMonitoramentoService:
    """One worker cycle: collects every due device in parallel; returns how many were recorded."""

    def executar(self, app, sonda=None):
        with app.app_context():
            ValidarConfiguracaoMonitorService().executar(app.config)
            ids = DispositivoRepository.ids_devidos_para_coleta(utcnow(), limite=500)
        coletar = ColetarDispositivoService()
        with ThreadPoolExecutor(max_workers=app.config['MONITOR_WORKERS']) as pool:
            return sum(pool.map(lambda id: coletar.executar(app, id, sonda), ids))
