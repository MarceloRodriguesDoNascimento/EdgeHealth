from collections import Counter
from datetime import timedelta
from flask import g, request
from sqlalchemy import select, func
from werkzeug.exceptions import BadRequest
from ..extensions import db
from models import Coletor, Dispositivo,Metrica, Falha, Diagnostico, iso, utcnow
from .. import validation as v
from .management import scoped_device
from .serialization import metric_dict, failure_dict, device_dict


def date_filter(query,column,start,end):
    if start: query=query.where(column>=start)
    if end: query=query.where(column<end)
    return query


def metric_query(default_days=7):
    query=select(Metrica).join(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id)
    device_id=v.query_int('dispositivo_id')
    if device_id:
        scoped_device(device_id)
        query=query.where(Metrica.dispositivo_id==device_id)
    metric_type=request.args.get('tipo')
    if metric_type and metric_type not in ('latencia','perda_pacotes','disponibilidade'):
        raise BadRequest('Tipo de métrica inválido.')
    start,end=v.period(default_days)
    return date_filter(query,Metrica.coletada_em,start,end)


def failure_query(default_days=None):
    query=select(Falha).join(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id)
    device_id=v.query_int('dispositivo_id')
    if device_id:
        scoped_device(device_id)
        query=query.where(Falha.dispositivo_id==device_id)
    for name,values in [('severidade',('BAIXA','MEDIA','ALTA','CRITICA')),('estado',('ABERTA','ENCERRADA'))]:
        value=request.args.get(name)
        if value:
            if value not in values: raise BadRequest(f'{name} inválido.')
            query=query.where(getattr(Falha,name)==value)
    start,end=v.period(default_days)
    return date_filter(query,Falha.inicio,start,end)


def paginate(query,serializer):
    page=v.query_int('pagina',1,1,100000)
    limit=v.query_int('limite',50,1,500)
    total=db.session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows=db.session.scalars(query.offset((page-1)*limit).limit(limit)).all()
    return dict(items=[serializer(x) for x in rows],total=total,pagina=page,limite=limit)


def dashboard():
    now=utcnow()
    devices=db.session.scalars(select(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id,Dispositivo.arquivado_em.is_(None))).all()
    failures=db.session.scalars(select(Falha).join(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id,Falha.estado=='ABERTA')).all()
    status=Counter(d.status or 'SEM_COLETA' for d in devices)
    counts=dict(total=len(devices),online=status['ONLINE'],instaveis=status['INSTAVEL'],offline=status['OFFLINE'],
                sem_coleta=status['SEM_COLETA'],falhas_abertas=len(failures),
                desatualizados=sum(device_dict(d)['desatualizado'] for d in devices))
    recent=db.session.scalars(select(Falha).join(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id).order_by(Falha.inicio.desc(),Falha.id.desc()).limit(8)).all()
    # Individual per-device series avoid combining different devices into a fictitious measurement.
    device_id=v.query_int('dispositivo_id')
    if device_id:
        scoped_device(device_id)
    elif devices:
        device_id=devices[0].id
    start,end=v.period(1)
    series=[]
    sample_total=0
    if device_id:
        q=date_filter(select(Metrica).where(Metrica.dispositivo_id==device_id),Metrica.coletada_em,start,end)
        sample_total=db.session.scalar(select(func.count()).select_from(q.subquery()))
        rows=db.session.scalars(q.order_by(Metrica.coletada_em.desc(),Metrica.id.desc()).limit(500)).all()
        series=[metric_dict(m) for m in reversed(rows)]
    from .collectors import collector_state
    collectors=[dict(id=c.id,nome=c.nome,estado=collector_state(c,now),ultimo_contato=iso(c.ultimo_contato),ultimo_erro=c.ultimo_erro)
                for c in db.session.scalars(select(Coletor).where(Coletor.empresa_id==g.user.empresa_id,Coletor.revogado_em.is_(None)).order_by(Coletor.nome))]
    return dict(coletores=collectors,indicadores=counts,severidades=dict(Counter(f.severidade for f in failures)),
                falhas_recentes=[failure_dict(f) for f in recent],serie=series,serie_total=sample_total,
                dispositivo_id=device_id,dispositivos=[device_dict(d) for d in devices],atualizado_em=iso(now),
                custos=cost_summary(now))


def cost_summary(now, days=30):
    """Estimated loss of the incidents started in the last `days` days (shared outages de-duplicated)."""
    from models import Empresa
    from .costs import total_for
    since=now-timedelta(days=days)
    failures=db.session.scalars(select(Falha).join(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id,
        Falha.inicio>=since).order_by(Falha.inicio)).all()
    result=total_for(failures,db.session.get(Empresa,g.user.empresa_id),now)
    result.pop('individual',None)
    return dict(result,dias=days)
