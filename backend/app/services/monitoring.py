import ipaddress
import logging
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from math import isfinite
from flask import current_app
from icmplib import ping
from icmplib.exceptions import ICMPLibError
from sqlalchemy import select, update, or_
from ..extensions import db
from ..models import Dispositivo, Metrica, Falha, Impacto, utcnow
from .diagnostics import refresh_company

log=logging.getLogger(__name__)

class CollectorError(Exception):
    """The collector could not execute a trustworthy measurement."""

@dataclass(frozen=True)
class ProbeResult:
    sent: int
    received: int
    latency_ms: float | None

    def __post_init__(self):
        if isinstance(self.sent,bool) or not isinstance(self.sent,int) or self.sent<=0:
            raise CollectorError('Quantidade de pacotes enviados inválida.')
        if not isinstance(self.received,int) or isinstance(self.received,bool) or not 0<=self.received<=self.sent:
            raise CollectorError('Quantidade de pacotes recebidos inválida.')
        if self.received and (self.latency_ms is None or not isfinite(self.latency_ms) or self.latency_ms<0):
            raise CollectorError('Latência inválida para uma resposta recebida.')
        if not self.received and self.latency_ms is not None:
            raise CollectorError('Sem resposta, a latência deve permanecer desconhecida.')

    @property
    def loss(self):
        return (self.sent-self.received)*100.0/self.sent


def real_probe(address, count=4, timeout=1):
    try:
        parsed=ipaddress.ip_address(address)
        if parsed.is_multicast or parsed.is_unspecified:
            raise ValueError('IP não permitido')
        host=ping(str(parsed),count=count,interval=0.2,timeout=timeout,privileged=False)
        return ProbeResult(host.packets_sent,host.packets_received,float(host.avg_rtt) if host.packets_received else None)
    except (ICMPLibError, OSError, ValueError) as error:
        raise CollectorError(f'Não foi possível executar o teste ICMP: {type(error).__name__}. Verifique permissões e rede do coletor.') from error


def classify(device,result):
    cfg=current_app.config
    if result.received==0:
        device.falhas_consecutivas+=1
        device.sucessos_consecutivos=0
        return 'OFFLINE' if device.falhas_consecutivas>=cfg['OFFLINE_AFTER'] else 'INSTAVEL'
    device.falhas_consecutivas=0
    degraded=result.loss>=cfg['LOSS_LIMIT_PCT'] or result.latency_ms>=cfg['LATENCY_LIMIT_MS']
    if degraded:
        device.sucessos_consecutivos=0
        return 'INSTAVEL'
    device.sucessos_consecutivos+=1
    if device.status in ('OFFLINE','INSTAVEL') and device.sucessos_consecutivos<cfg['RECOVERY_AFTER']:
        return 'INSTAVEL'
    return 'ONLINE'


def record_result(device,result,observed_at=None):
    """Caller owns transaction and device lease. No network I/O in this function."""
    now=observed_at or utcnow()
    device.status=classify(device,result)
    device.ultima_coleta=now
    device.latencia_ms=result.latency_ms
    device.perda_pacotes_pct=result.loss
    device.erro_coleta=None
    metric=Metrica(dispositivo_id=device.id,coletada_em=now,respondeu=bool(result.received),
        latencia_ms=result.latency_ms,pacotes_enviados=result.sent,pacotes_recebidos=result.received,
        perda_pacotes_pct=result.loss,status=device.status)
    db.session.add(metric)
    current=db.session.scalar(select(Falha).where(Falha.dispositivo_id==device.id,Falha.estado=='ABERTA'))
    if device.status!='ONLINE':
        kind='INDISPONIBILIDADE' if device.status=='OFFLINE' else 'INSTABILIDADE'
        if not current:
            current=Falha(dispositivo_id=device.id,tipo=kind,estado='ABERTA',inicio=now,ultima_observacao=now,
                          descricao='Anomalia detectada por teste de conectividade.')
            db.session.add(current)
            db.session.flush()
            db.session.add(Impacto(falha_id=current.id))
            log.info('Ocorrência aberta dispositivo=%s falha=%s',device.id,current.id)
        # Preserve worst condition observed in the same occurrence.
        if kind=='INDISPONIBILIDADE':
            current.tipo=kind
        current.ultima_observacao=now
    elif current:
        current.estado='ENCERRADA'
        current.fim=now
        current.ultima_observacao=now
        current.encerramento='RECUPERACAO'
        log.info('Ocorrência encerrada dispositivo=%s falha=%s',device.id,current.id)
    db.session.flush()
    refresh_company(device.empresa_id,now,extra_failure=current)
    return metric


def validate_monitor_config(cfg):
    if not 1<=cfg['MONITOR_PACKETS']<=10 or not 0.1<=cfg['MONITOR_TIMEOUT']<=10:
        raise ValueError('MONITOR_PACKETS deve estar entre 1 e 10 e MONITOR_TIMEOUT entre 0.1 e 10.')
    if not 1<=cfg['MONITOR_INTERVAL']<=86400 or not 1<=cfg['MONITOR_WORKERS']<=16:
        raise ValueError('Intervalo ou quantidade de workers inválida.')
    bound=cfg['MONITOR_PACKETS']*(cfg['MONITOR_TIMEOUT']+0.2)+10
    if cfg['MONITOR_LEASE_SECONDS']<=bound:
        raise ValueError('MONITOR_LEASE_SECONDS deve superar a duração máxima da coleta com margem de 10 segundos.')
    if cfg['OFFLINE_AFTER']<2 or cfg['RECOVERY_AFTER']<1 or cfg['LATENCY_LIMIT_MS']<=0 or not 0<cfg['LOSS_LIMIT_PCT']<=100:
        raise ValueError('Limites de classificação inválidos.')


def collect_device(app,device_id,probe=None):
    with app.app_context():
        validate_monitor_config(app.config)
        now=utcnow()
        owner=secrets.token_hex(16)
        claimed=db.session.execute(update(Dispositivo).where(Dispositivo.id==device_id,
            Dispositivo.arquivado_em.is_(None),Dispositivo.proxima_coleta<=now,
            or_(Dispositivo.lease_until.is_(None),Dispositivo.lease_until<now)).values(
                lease_owner=owner,lease_until=now+timedelta(seconds=app.config['MONITOR_LEASE_SECONDS'])))
        db.session.commit()
        if not claimed.rowcount:
            return False
        device=db.session.get(Dispositivo,device_id)
        address=device.ip
        db.session.remove()  # Never keep a database transaction open while probing.
        try:
            result=(probe or real_probe)(address,app.config['MONITOR_PACKETS'],app.config['MONITOR_TIMEOUT'])
            device=db.session.get(Dispositivo,device_id)
            if device.lease_owner!=owner or device.arquivado_em:
                return False
            record_result(device,result)
            device.proxima_coleta=utcnow()+timedelta(seconds=app.config['MONITOR_INTERVAL'])
            device.lease_owner=device.lease_until=None
            db.session.commit()
            log.info('Coleta concluída dispositivo=%s recebidos=%s enviados=%s',device_id,result.received,result.sent)
            return True
        except Exception as error:
            db.session.rollback()
            message=str(error) if isinstance(error,CollectorError) else 'Erro interno na coleta; consulte os logs do worker.'
            log.exception('Coleta não concluída dispositivo=%s',device_id)
            db.session.execute(update(Dispositivo).where(Dispositivo.id==device_id,Dispositivo.lease_owner==owner).values(
                erro_coleta=message[:500],lease_owner=None,lease_until=None,
                proxima_coleta=utcnow()+timedelta(seconds=app.config['MONITOR_INTERVAL'])))
            db.session.commit()
            return False
        finally:
            db.session.remove()


def run_cycle(app,probe=None):
    with app.app_context():
        validate_monitor_config(app.config)
        ids=list(db.session.scalars(select(Dispositivo.id).where(Dispositivo.arquivado_em.is_(None),
            Dispositivo.proxima_coleta<=utcnow()).order_by(Dispositivo.proxima_coleta).limit(500)))
    with ThreadPoolExecutor(max_workers=app.config['MONITOR_WORKERS']) as pool:
        return sum(pool.map(lambda id: collect_device(app,id,probe),ids))
