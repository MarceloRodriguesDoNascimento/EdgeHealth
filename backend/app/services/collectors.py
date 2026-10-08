"""Remote collectors: credentials, authentication and HTTPS ingestion.

The collector only measures (packets sent/received and latency). Status, incidents,
severity and diagnosis are always derived here, by the same record_result pipeline
used by the local worker.
"""
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from itertools import groupby
from flask import current_app, g, request
from sqlalchemy import select, update
from werkzeug.exceptions import BadRequest, Conflict, NotFound, TooManyRequests, Unauthorized
from ..extensions import db
from models import Coletor, Dispositivo, Metrica, iso, utcnow
from .. import validation as v
from .auth import digest
from .monitoring import ProbeResult, CollectorError, claim_device, record_result

log = logging.getLogger(__name__)
TOKEN_PREFIX = 'ehc_'
ERROR_TYPES = ('PERMISSAO_ICMP', 'FALHA_COLETOR')


def new_token():
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return token, digest(token), token[:12]


def collector_state(c, now=None):
    if c.revogado_em:
        return 'REVOGADO'
    if not c.ultimo_contato:
        return 'NUNCA_CONECTADO'
    age = ((now or utcnow()) - c.ultimo_contato).total_seconds()
    return 'DESATUALIZADO' if age > current_app.config['COLLECTOR_STALE_SECONDS'] else 'ATIVO'


def collector_dict(c):
    devices = db.session.scalars(select(Dispositivo.id).where(Dispositivo.coletor_id == c.id,
                                                                Dispositivo.arquivado_em.is_(None))).all()
    return dict(id=c.id, nome=c.nome, token_prefixo=c.token_prefixo, estado=collector_state(c),
                criado_em=iso(c.criado_em), rotacionado_em=iso(c.rotacionado_em), revogado_em=iso(c.revogado_em),
                ultimo_contato=iso(c.ultimo_contato), versao=c.versao, fila_pendente=c.fila_pendente,
                ultimo_erro=c.ultimo_erro, ultimo_erro_em=iso(c.ultimo_erro_em), dispositivos=len(devices))


# --- Administration (user session, admin role) -------------------------------------------

def scoped_collector(id):
    c = db.session.scalar(select(Coletor).where(Coletor.id == id, Coletor.empresa_id == g.user.empresa_id))
    if not c:
        raise NotFound('Coletor não encontrado.')
    return c


def create_collector(name):
    token, token_hash, prefix = new_token()
    c = Coletor(empresa_id=g.user.empresa_id, nome=v.string(name, 'Nome', 100), token_hash=token_hash, token_prefixo=prefix)
    db.session.add(c)
    db.session.commit()
    log.info('Coletor criado empresa=%s coletor=%s prefixo=%s', c.empresa_id, c.id, prefix)
    return c, token


def rotate_collector(id):
    c = scoped_collector(id)
    if c.revogado_em:
        raise Conflict('Coletor revogado não pode receber nova credencial. Cadastre outro coletor.')
    token, c.token_hash, c.token_prefixo = new_token()
    c.rotacionado_em = utcnow()
    db.session.commit()
    log.info('Credencial rotacionada coletor=%s prefixo=%s', c.id, c.token_prefixo)
    return c, token


def revoke_collector(id):
    c = scoped_collector(id)
    if not c.revogado_em:
        c.revogado_em = utcnow()
        db.session.commit()
        log.info('Coletor revogado coletor=%s', c.id)
    return c


def assignable_collector(value):
    """Validates a coletor_id sent with a device form: same company and not revoked."""
    if value is None:
        return None
    id = v.integer(value, 'Coletor', 1, 2147483647)
    c = db.session.scalar(select(Coletor).where(Coletor.id == id, Coletor.empresa_id == g.user.empresa_id))
    if not c:
        raise NotFound('Coletor não encontrado.')
    if c.revogado_em:
        raise Conflict('O coletor está revogado.')
    return c.id


# --- Collector authentication ---------------------------------------------------------------

def require_collector(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        token = header[7:].strip() if header.startswith('Bearer ') else ''
        c = db.session.scalar(select(Coletor).where(Coletor.token_hash == digest(token))) if token.startswith(TOKEN_PREFIX) else None
        if not c or c.revogado_em:
            raise Unauthorized('Credencial de coletor inválida ou revogada.')
        now = utcnow()
        cfg = current_app.config
        if not c.janela_inicio or (now - c.janela_inicio).total_seconds() >= 60:
            c.janela_inicio, c.janela_requisicoes = now, 0
        if c.janela_requisicoes >= cfg['COLLECTOR_MAX_REQUESTS_PER_MINUTE']:
            db.session.commit()
            raise TooManyRequests('Limite de requisições do coletor excedido. Aguarde e tente novamente.')
        c.janela_requisicoes += 1
        c.ultimo_contato = now
        db.session.commit()
        request.max_content_length = cfg['COLLECTOR_MAX_CONTENT_LENGTH']
        g.collector = c
        return fn(*args, **kwargs)
    return wrapped


def assigned_devices(c):
    return db.session.scalars(select(Dispositivo).where(Dispositivo.coletor_id == c.id, Dispositivo.empresa_id == c.empresa_id,
                                                        Dispositivo.arquivado_em.is_(None)).order_by(Dispositivo.id)).all()


def collector_config():
    cfg = current_app.config
    c = g.collector
    return dict(coletor_id=c.id, servidor_em=iso(utcnow()), intervalo_segundos=cfg['MONITOR_INTERVAL'],
                pacotes=cfg['MONITOR_PACKETS'], timeout_segundos=cfg['MONITOR_TIMEOUT'],
                lote_maximo=cfg['COLLECTOR_MAX_BATCH'],
                dispositivos=[dict(id=d.id, ip=d.ip, proxima_coleta=iso(d.proxima_coleta)) for d in assigned_devices(c)])


def heartbeat(data):
    c = g.collector
    if 'versao' in data:
        c.versao = v.string(data['versao'], 'Versão', 30)
    if 'fila_pendente' in data:
        c.fila_pendente = v.integer(data['fila_pendente'], 'Fila pendente', 0, 1000000)
    if data.get('erro'):
        record_collector_error(c, data['erro'], None)
    elif 'erro' in data:
        c.ultimo_erro = None
    db.session.commit()
    return dict(estado=collector_state(c), servidor_em=iso(utcnow()))


def record_collector_error(c, item, devices):
    if not isinstance(item, dict) or item.get('tipo') not in ERROR_TYPES:
        raise BadRequest('Erro do coletor inválido.')
    message = v.string(item.get('mensagem') or item['tipo'], 'Mensagem', 300)
    label = 'Coletor sem permissão para ICMP' if item['tipo'] == 'PERMISSAO_ICMP' else 'Falha no coletor'
    c.ultimo_erro = f'{label}: {message}'[:500]
    c.ultimo_erro_em = utcnow()
    if devices is not None:
        # The device was NOT measured: no sample, no status change, no incident.
        for device in devices:
            device.erro_coleta = c.ultimo_erro
            device.proxima_coleta = utcnow() + timedelta(seconds=current_app.config['MONITOR_INTERVAL'])


# --- Ingestion ------------------------------------------------------------------------------

def parse_timestamp(raw):
    if not isinstance(raw, str):
        raise ValueError('coletada_em ausente')
    value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if not value.tzinfo:
        raise ValueError('coletada_em deve informar o fuso (UTC)')
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_sample(item, now):
    cfg = current_app.config
    if not isinstance(item, dict):
        raise ValueError('amostra deve ser um objeto')
    unknown = set(item) - {'id', 'dispositivo_id', 'coletada_em', 'enviados', 'recebidos', 'latencia_ms'}
    if unknown:
        raise ValueError('campos não permitidos: ' + ', '.join(sorted(unknown)))
    uid = str(uuid.UUID(str(item.get('id'))))
    device_id = item.get('dispositivo_id')
    if isinstance(device_id, bool) or not isinstance(device_id, int):
        raise ValueError('dispositivo_id inválido')
    observed = parse_timestamp(item.get('coletada_em'))
    if observed > now + timedelta(seconds=cfg['COLLECTOR_MAX_CLOCK_SKEW_SECONDS']):
        raise ValueError('coletada_em no futuro; verifique o relógio do coletor')
    if observed < now - timedelta(hours=cfg['COLLECTOR_MAX_SAMPLE_AGE_HOURS']):
        raise ValueError('amostra mais antiga que o limite aceito')
    latency = item.get('latencia_ms')
    if latency is not None and (isinstance(latency, bool) or not isinstance(latency, (int, float))):
        raise ValueError('latencia_ms inválida')
    sent = item.get('enviados')
    if isinstance(sent, int) and not isinstance(sent, bool) and sent > 100:
        raise ValueError('enviados acima do limite')
    try:
        result = ProbeResult(sent, item.get('recebidos'), float(latency) if latency is not None else None)
    except CollectorError as error:
        raise ValueError(str(error)) from error
    return uid, device_id, observed, result


def ingest(data):
    cfg = current_app.config
    c = g.collector
    samples = data.get('amostras', [])
    errors = data.get('erros', [])
    if not isinstance(samples, list) or not isinstance(errors, list):
        raise BadRequest('amostras e erros devem ser listas.')
    if len(samples) + len(errors) > cfg['COLLECTOR_MAX_BATCH']:
        raise BadRequest(f'Lote acima do limite de {cfg["COLLECTOR_MAX_BATCH"]} itens.')
    now = utcnow()
    allowed = {d.id: d for d in assigned_devices(c)}
    results, parsed, seen = [], [], set()
    for item in samples:
        uid = item.get('id') if isinstance(item, dict) else None
        try:
            uid, device_id, observed, result = parse_sample(item, now)
        except (ValueError, TypeError) as error:
            results.append(dict(id=uid, resultado='REJEITADA', motivo=str(error)[:200]))
            continue
        if device_id not in allowed:
            results.append(dict(id=uid, resultado='REJEITADA', motivo='dispositivo não atribuído a este coletor'))
        elif uid in seen:
            results.append(dict(id=uid, resultado='DUPLICADA'))
        else:
            seen.add(uid)
            parsed.append((device_id, observed, uid, result))
    for item in errors:
        device_id = item.get('dispositivo_id') if isinstance(item, dict) else None
        if device_id is not None and device_id not in allowed:
            raise BadRequest('Erro informado para dispositivo não atribuído a este coletor.')
        record_collector_error(c, item, [allowed[device_id]] if device_id is not None else [])
    db.session.commit()
    parsed.sort(key=lambda p: (p[0], p[1]))
    for device_id, group in groupby(parsed, key=lambda p: p[0]):
        results.extend(ingest_device(c, device_id, list(group)))
    return dict(recebidas=len(samples), resultados=results, servidor_em=iso(utcnow()))


def ingest_device(c, device_id, group):
    owner = claim_device(device_id, Dispositivo.coletor_id == c.id, Dispositivo.empresa_id == c.empresa_id)
    if not owner:
        # Lease held by a concurrent request: the collector keeps the samples queued and retries.
        return [dict(id=uid, resultado='TENTAR_NOVAMENTE', motivo='dispositivo em processamento') for _, _, uid, _ in group]
    out = []
    try:
        existing = set(db.session.scalars(select(Metrica.amostra_uid).where(Metrica.coletor_id == c.id,
                                                                            Metrica.amostra_uid.in_([p[2] for p in group]))))
        device = db.session.get(Dispositivo, device_id)
        received = utcnow()
        for _, observed, uid, result in group:
            if uid in existing:
                out.append(dict(id=uid, resultado='DUPLICADA'))
                continue
            metric = record_result(device, result, observed,
                                   dict(coletor_id=c.id, amostra_uid=uid, recebida_em=received))
            out.append(dict(id=uid, resultado='ATRASADA' if metric.fora_de_ordem else 'ACEITA'))
        device.proxima_coleta = utcnow() + timedelta(seconds=current_app.config['MONITOR_INTERVAL'])
        device.lease_owner = device.lease_until = None
        db.session.commit()
        return out
    except Exception:
        db.session.rollback()
        log.exception('Ingestão não concluída coletor=%s dispositivo=%s', c.id, device_id)
        db.session.execute(update(Dispositivo).where(Dispositivo.id == device_id, Dispositivo.lease_owner == owner)
                           .values(lease_owner=None, lease_until=None))
        db.session.commit()
        return [dict(id=uid, resultado='TENTAR_NOVAMENTE', motivo='erro interno') for _, _, uid, _ in group]
