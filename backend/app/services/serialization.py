from flask import current_app
from sqlalchemy import select
from ..extensions import db
from ..models import Coletor, Dispositivo,Diagnostico, DiagnosticoRecomendacao, Impacto, Recomendacao, iso, utcnow


def company_dict(e):
    return {k: getattr(e,k) for k in ('id','nome_fantasia','cnpj','email','telefone')}


def user_dict(u):
    result = {k: getattr(u,k) for k in ('id','nome','email','empresa_id','papel','ativo','termos_versao')}
    result['termos_pendentes'] = u.termos_versao != current_app.config['TERMS_VERSION']
    return result


def device_dict(d):
    result = {k: getattr(d,k) for k in ('id','empresa_id','nome','ip','tipo','localizacao','status','latencia_ms','perda_pacotes_pct','erro_coleta','coletor_id')}
    result.update(ultima_coleta=iso(d.ultima_coleta), arquivado_em=iso(d.arquivado_em),
                  desatualizado=not d.ultima_coleta or (utcnow()-d.ultima_coleta).total_seconds() > current_app.config['STALE_AFTER_SECONDS'])
    if d.coletor_id:
        from .collectors import collector_state
        collector = db.session.get(Coletor, d.coletor_id)
        result.update(coletor=collector.nome, coletor_estado=collector_state(collector))
    else:
        result.update(coletor=None, coletor_estado=None)
    return result


def metric_dict(m):
    result = {k: getattr(m,k) for k in ('id','dispositivo_id','respondeu','latencia_ms','pacotes_enviados','pacotes_recebidos','perda_pacotes_pct','status','coletor_id','fora_de_ordem')}
    result.update(coletada_em=iso(m.coletada_em), recebida_em=iso(m.recebida_em))
    return result


def recommendation_dict(r):
    return {k:getattr(r,k) for k in ('id','regra','codigo','titulo','acao')}


def diagnostic_dict(diag):
    if not diag:
        return None
    recs = db.session.scalars(select(Recomendacao).join(DiagnosticoRecomendacao, DiagnosticoRecomendacao.recomendacao_id == Recomendacao.id).where(DiagnosticoRecomendacao.diagnostico_id == diag.id).order_by(Recomendacao.id)).all()
    return dict(id=diag.id, falha_id=diag.falha_id, descricao=diag.descricao, causas=diag.causas,
                evidencias=diag.evidencias, estado=diag.estado, analisado_em=iso(diag.analisado_em),
                versao_regras=diag.versao_regras, recomendacoes=[recommendation_dict(r) for r in recs])


def failure_dict(f, detail=False):
    device = db.session.get(Dispositivo,f.dispositivo_id)
    impact = db.session.scalar(select(Impacto).where(Impacto.falha_id==f.id))
    duration = max(0, ((f.fim or utcnow())-f.inicio).total_seconds())
    result = dict(id=f.id, dispositivo_id=f.dispositivo_id, dispositivo=device.nome, ip=device.ip,
                  localizacao=device.localizacao, tipo=f.tipo, estado=f.estado, inicio=iso(f.inicio), fim=iso(f.fim),
                  ultima_observacao=iso(f.ultima_observacao), descricao=f.descricao, severidade=f.severidade,
                  justificativa=f.justificativa, duracao_segundos=round(duration,1), encerramento=f.encerramento,
                  impacto=dict(usuarios_afetados=impact.usuarios_afetados, origem=impact.origem,
                               observacao=impact.observacao, atualizado_em=iso(impact.atualizado_em)) if impact else None)
    if detail:
        result['diagnostico'] = diagnostic_dict(db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id==f.id)))
    return result
