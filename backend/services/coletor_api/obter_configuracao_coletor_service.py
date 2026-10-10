from flask import current_app
from models import iso, utcnow
from repositories import DispositivoRepository


class ObterConfiguracaoColetorService:
    """What the collector must measure, how and how often."""

    def executar(self, coletor):
        cfg = current_app.config
        return dict(coletor_id=coletor.id, servidor_em=iso(utcnow()), intervalo_segundos=cfg['MONITOR_INTERVAL'],
                    pacotes=cfg['MONITOR_PACKETS'], timeout_segundos=cfg['MONITOR_TIMEOUT'],
                    lote_maximo=cfg['COLLECTOR_MAX_BATCH'],
                    dispositivos=[dict(id=d.id, ip=d.ip, proxima_coleta=iso(d.proxima_coleta))
                                  for d in DispositivoRepository.listar_do_coletor(coletor.id, coletor.empresa_id)])
