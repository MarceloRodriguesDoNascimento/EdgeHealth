from datetime import timedelta
from flask import current_app
from sqlalchemy import select, delete, func
from ..extensions import db
from ..models import Dispositivo, Metrica, Falha, Impacto, Diagnostico, DiagnosticoRecomendacao, Recomendacao, iso, utcnow


def recalculate_severity(failure, related_count, now):
    cfg = current_app.config
    impact = db.session.scalar(select(Impacto).where(Impacto.falha_id == failure.id))
    minutes = max(0, ((failure.fim or now)-failure.inicio).total_seconds()/60)
    users = impact.usuarios_afetados if impact else None
    level, reasons = 0, []
    if failure.tipo == 'INDISPONIBILIDADE':
        level = 1
        reasons.append('Dispositivo sem resposta após confirmação de indisponibilidade.')
    for threshold, target in [(cfg['SEVERITY_MEDIUM_MINUTES'],1), (cfg['SEVERITY_HIGH_MINUTES'],2), (cfg['SEVERITY_CRITICAL_MINUTES'],3)]:
        if minutes >= threshold:
            level = max(level,target)
            reasons.append(f'Duração de pelo menos {threshold} minutos.')
    if related_count >= cfg['SEVERITY_GROUP_SIZE']:
        level = max(level,2)
        reasons.append(f'{related_count} dispositivos com ocorrências temporalmente relacionadas.')
    if users is not None:
        if users >= cfg['SEVERITY_HIGH_USERS']:
            level = max(level,2)
            reasons.append(f'Estimativa informada de {users} usuários afetados.')
        if users >= cfg['SEVERITY_CRITICAL_USERS']:
            level = 3
    if not reasons:
        reasons.append('Instabilidade observada, abaixo dos limites de escalonamento.')
    failure.severidade = ['BAIXA','MEDIA','ALTA','CRITICA'][level]
    failure.justificativa = dict(motivos=reasons, duracao_minutos=round(minutes,2),
                                dispositivos_afetados=related_count, usuarios_afetados=users,
                                calculada_em=iso(now), versao_regras='1.0')


def analyze(failure, related, now):
    cfg = current_app.config
    device = db.session.get(Dispositivo, failure.dispositivo_id)
    window_start = now-timedelta(seconds=cfg['DIAGNOSTIC_WINDOW_SECONDS'])
    samples = db.session.scalars(select(Metrica).where(Metrica.dispositivo_id==device.id,
        Metrica.coletada_em>=window_start, Metrica.coletada_em<=now).order_by(Metrica.coletada_em.desc(),Metrica.id.desc()).limit(20)).all()
    diag=db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id==failure.id))
    # Re-analysis triggered by another device's sample (e.g. a collector catching up after an
    # outage) may find no sample of this device in the window: that is missing data, not new
    # evidence, so it must not replace the existing explanation with EVIDENCIA_INSUFICIENTE.
    if not samples and diag:
        return diag
    latest=samples[0] if samples else None
    recovering = (latest and latest.status == 'INSTAVEL' and latest.respondeu
                  and latest.latencia_ms is not None and latest.latencia_ms < cfg['LATENCY_LIMIT_MS']
                  and latest.perda_pacotes_pct < cfg['LOSS_LIMIT_PCT'])
    # The first healthy sample confirms recovery but must not erase the last
    # explanation of the anomaly that will be shown in the closed incident.
    if recovering and diag:
        return diag
    peers = db.session.scalars(select(Dispositivo).where(Dispositivo.empresa_id==device.empresa_id,
        Dispositivo.id!=device.id, Dispositivo.arquivado_em.is_(None),
        Dispositivo.ultima_coleta>=window_start, Dispositivo.ultima_coleta<=now)).all()
    previous = list(db.session.scalars(select(Falha.id).where(Falha.dispositivo_id==device.id,
        Falha.id!=failure.id, Falha.inicio>=now-timedelta(days=7), Falha.inicio<=now).order_by(Falha.inicio.desc()).limit(20)))
    causes=[]
    if latest and latest.status=='OFFLINE' and any(p.status=='ONLINE' for p in peers):
        causes.append(dict(regra='LOCALIZADA', descricao='Possível problema localizado no dispositivo, alimentação, cabo, porta ou política de resposta ICMP; outros dispositivos da empresa responderam.'))
    # Correlation uses the incidents, not the peers' status at this instant: in a group outage
    # the peers recover in collector/batch order, and an analysis between two recoveries must
    # not drop COMPARTILHADA from the device still offline. A peer counts when its confirmed
    # unavailability overlapped this one and either already ended (observed outage) or is
    # still open with a current observation (stale peers are not evidence).
    current_peers = {p.id for p in peers}
    shared = {device.id} | {f.dispositivo_id for f in related
                            if f.tipo=='INDISPONIBILIDADE' and f.dispositivo_id!=device.id
                            and ((f.estado=='ABERTA' and f.dispositivo_id in current_peers)
                                 or (f.estado=='ENCERRADA' and f.fim and f.fim>=failure.inicio))}
    if latest and latest.status=='OFFLINE' and len(shared)>=2:
        causes.append(dict(regra='COMPARTILHADA', descricao='Possível interrupção de infraestrutura compartilhada: vários dispositivos ficaram indisponíveis em uma janela semelhante. A topologia não foi determinada.'))
    if latest and latest.respondeu and latest.latencia_ms is not None:
        if latest.latencia_ms>=cfg['LATENCY_LIMIT_MS'] and latest.perda_pacotes_pct>=cfg['LOSS_LIMIT_PCT']:
            causes.append(dict(regra='CONGESTIONAMENTO', descricao='Possível congestionamento ou enlace instável: latência e perda de pacotes elevadas na amostra recente.'))
        elif latest.latencia_ms>=cfg['LATENCY_LIMIT_MS']:
            causes.append(dict(regra='LATENCIA', descricao='Possível saturação ou caminho de rede degradado: latência elevada com perda abaixo do limite.'))
    if latest and len(previous)>=2:
        causes.append(dict(regra='RECORRENTE', descricao='Possível instabilidade recorrente de conectividade: há pelo menos duas outras ocorrências nos últimos sete dias.'))
    if not diag:
        diag=Diagnostico(falha_id=failure.id)
        db.session.add(diag)
    diag.causas=causes
    diag.estado='DISPONIVEL' if causes else 'EVIDENCIA_INSUFICIENTE'
    diag.descricao=('Análise por regras a partir das medições e ocorrências relacionadas. As causas são hipóteses.'
                    if causes else 'Não há evidências suficientes para determinar uma causa provável.')
    diag.analisado_em=now
    diag.evidencias=dict(dispositivo_id=device.id, status=device.status,
        amostras=[dict(id=m.id,coletada_em=iso(m.coletada_em),latencia_ms=m.latencia_ms,perda_pacotes_pct=m.perda_pacotes_pct,status=m.status) for m in samples],
        outros_dispositivos=[dict(id=p.id,status=p.status,ultima_coleta=iso(p.ultima_coleta)) for p in peers],
        falhas_relacionadas=[f.id for f in related], ocorrencias_anteriores=previous,
        janela_segundos=cfg['DIAGNOSTIC_WINDOW_SECONDS'],
        limites=dict(latencia_ms=cfg['LATENCY_LIMIT_MS'],perda_pacotes_pct=cfg['LOSS_LIMIT_PCT']))
    db.session.flush()
    db.session.execute(delete(DiagnosticoRecomendacao).where(DiagnosticoRecomendacao.diagnostico_id==diag.id))
    rules=[c['regra'] for c in causes]
    if rules:
        for rec in db.session.scalars(select(Recomendacao).where(Recomendacao.regra.in_(rules))):
            db.session.add(DiagnosticoRecomendacao(diagnostico_id=diag.id,recomendacao_id=rec.id))
    return diag


def refresh_company(company_id, now=None, extra_failure=None):
    now=now or utcnow()
    window=current_app.config['DIAGNOSTIC_WINDOW_SECONDS']
    failures=db.session.scalars(select(Falha).join(Dispositivo).where(Dispositivo.empresa_id==company_id,Falha.estado=='ABERTA')).all()
    if extra_failure and extra_failure.id not in {f.id for f in failures}:
        failures.append(extra_failure)
    # Incidents already closed still belong to the same event: without them, the severity
    # group and the shared-outage hypothesis of the last open incidents would shrink as the
    # other devices recover.
    pool=list(failures)
    if failures:
        earliest=min(f.inicio for f in failures)-timedelta(seconds=window)
        ids={f.id for f in failures}
        pool+=[f for f in db.session.scalars(select(Falha).join(Dispositivo).where(Dispositivo.empresa_id==company_id,
               Falha.estado=='ENCERRADA',Falha.inicio>=earliest)) if f.id not in ids]
    for failure in failures:
        related=[f for f in pool if abs((f.inicio-failure.inicio).total_seconds())<=window]
        recalculate_severity(failure,len({f.dispositivo_id for f in related}),now)
        # Keep the diagnosis that explained an incident at its last anomalous observation.
        if failure.estado=='ABERTA':
            analyze(failure,related,now)
    db.session.flush()
