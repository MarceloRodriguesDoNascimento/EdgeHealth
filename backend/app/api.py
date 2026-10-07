from flask import Blueprint, g, jsonify, request, current_app, send_file
from pathlib import Path
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import select, text, inspect
from werkzeug.exceptions import BadRequest, NotFound, Conflict
from .extensions import db
from .models import Empresa, Usuario, Dispositivo, Metrica, Falha, Impacto, Diagnostico, Recomendacao, Coletor, utcnow
from . import validation as v
from .services import management as management
from .services import collectors as collectors_service
from .services.auth import require_auth, login, issue_session
from .services.serialization import company_dict,user_dict,device_dict,metric_dict,failure_dict,diagnostic_dict,recommendation_dict
from .services.queries import paginate,metric_query,failure_query,dashboard
from .services.diagnostics import refresh_company
from .services.reports import export_report

api=Blueprint('api',__name__,url_prefix='/api')

@api.get('/health')
def health():
    db.session.execute(text('SELECT 1'))
    tables=inspect(db.engine).get_table_names()
    scripts=ScriptDirectory(str(Path(__file__).resolve().parents[1] / 'migrations'))
    with db.engine.connect() as connection:
        current=set(MigrationContext.configure(connection).get_current_heads())
    ready=set(db.metadata.tables).issubset(tables) and current==set(scripts.get_heads())
    return jsonify(status='ok' if ready else 'migrations_pendentes'),200 if ready else 503

@api.get('/termos')
def terms_version():
    return jsonify(versao=current_app.config['TERMS_VERSION'])

@api.post('/auth/registro')
def register():
    data=v.payload(['nome_fantasia','cnpj','telefone','nome','email','senha','aceite_termos'],['nome_fantasia','cnpj','nome','email','senha'])
    user=management.create_company_account(data)
    response=jsonify(usuario=user_dict(user),empresa=company_dict(db.session.get(Empresa,user.empresa_id)))
    response.status_code=201
    return issue_session(user,response)

@api.post('/auth/login')
def authenticate():
    data=v.payload(['email','senha'],['email','senha'])
    user=login(v.email(data['email']),v.password(data['senha'], minimum=1))
    return issue_session(user,jsonify(usuario=user_dict(user),empresa=company_dict(db.session.get(Empresa,user.empresa_id))))

@api.get('/auth/me')
@require_auth(terms=False)
def me():
    return jsonify(usuario=user_dict(g.user),empresa=company_dict(db.session.get(Empresa,g.user.empresa_id)))

@api.post('/auth/aceite-termos')
@require_auth(terms=False)
def accept_terms():
    data=v.payload(['aceite_termos'],['aceite_termos'])
    if data['aceite_termos'] is not True: raise BadRequest('Confirme o aceite dos Termos de Uso.')
    management.accept_terms(g.user)
    db.session.commit()
    return jsonify(usuario=user_dict(g.user),empresa=company_dict(db.session.get(Empresa,g.user.empresa_id)))

@api.post('/auth/logout')
@require_auth(terms=False)
def logout():
    db.session.delete(g.auth_session)
    db.session.commit()
    response=current_app.response_class(status=204)
    response.delete_cookie(current_app.config['SESSION_COOKIE_NAME'],path='/')
    response.delete_cookie('edgehealth_csrf',path='/')
    return response

@api.get('/empresa')
@require_auth()
def company():
    return jsonify(company_dict(db.session.get(Empresa,g.user.empresa_id)))

@api.put('/empresa')
@require_auth(admin=True)
def update_company():
    return jsonify(company_dict(management.update_company(v.payload(['nome_fantasia','cnpj','email','telefone']))))

@api.put('/empresa/custos')
@require_auth(admin=True)
def update_company_costs():
    return jsonify(company_dict(management.update_company_costs(v.payload(
        ['salario_medio','fator_encargos','horas_mes','total_funcionarios','expediente','fuso']))))

@api.post('/empresa/custos/pular')
@require_auth(admin=True)
def skip_cost_assistant():
    v.payload([])
    return jsonify(company_dict(management.skip_cost_assistant()))

@api.get('/usuarios')
@require_auth(admin=True)
def users():
    return jsonify([user_dict(u) for u in db.session.scalars(select(Usuario).where(Usuario.empresa_id==g.user.empresa_id).order_by(Usuario.nome))])

@api.post('/usuarios')
@require_auth(admin=True)
def create_user():
    return jsonify(user_dict(management.save_user(v.payload(['nome','email','senha','papel'],['nome','email','senha'])))),201

@api.put('/usuarios/<int:id>')
@require_auth(admin=True)
def update_user(id):
    return jsonify(user_dict(management.save_user(v.payload(['nome','email','senha','papel','ativo']),id)))

@api.get('/dispositivos')
@require_auth()
def devices():
    query=select(Dispositivo).where(Dispositivo.empresa_id==g.user.empresa_id)
    archived=request.args.get('arquivados','0')
    if archived not in ('0','1'): raise BadRequest('arquivados deve ser 0 ou 1.')
    if archived=='0': query=query.where(Dispositivo.arquivado_em.is_(None))
    return jsonify([device_dict(d) for d in db.session.scalars(query.order_by(Dispositivo.nome,Dispositivo.id))])

@api.get('/dispositivos/<int:id>')
@require_auth()
def device(id):
    return jsonify(device_dict(management.scoped_device(id)))

@api.post('/dispositivos')
@require_auth()
def create_device():
    return jsonify(device_dict(management.save_device(v.payload(['nome','ip','tipo','localizacao','coletor_id','usuarios_dependentes','perda_produtividade_pct','receita_hora_dependente'],['nome','ip','tipo','localizacao'])))),201

@api.put('/dispositivos/<int:id>')
@require_auth()
def update_device(id):
    return jsonify(device_dict(management.save_device(v.payload(['nome','ip','tipo','localizacao','coletor_id','usuarios_dependentes','perda_produtividade_pct','receita_hora_dependente']),id)))


@api.get('/dispositivos/impacto-padrao')
@require_auth()
def device_impact_default():
    from .services.costs import defaults
    return jsonify(defaults(request.args.get('tipo',''),db.session.get(Empresa,g.user.empresa_id)))

@api.delete('/dispositivos/<int:id>')
@require_auth()
def archive_device(id):
    management.archive_device(id)
    return '',204

@api.post('/dispositivos/<int:id>/desarquivar')
@require_auth()
def restore_device(id):
    v.payload([])
    return jsonify(device_dict(management.restore_device(id)))

@api.post('/dispositivos/<int:id>/coletas')
@require_auth()
def request_collection(id):
    v.payload([])
    d=management.scoped_device(id,False)
    if d.lease_until and d.lease_until>utcnow(): raise Conflict('Uma coleta já está em andamento.')
    d.proxima_coleta=utcnow()
    db.session.commit()
    who='O coletor remoto a executará ao sincronizar a configuração.' if d.coletor_id else 'O worker a executará no próximo ciclo.'
    return jsonify(mensagem='Coleta solicitada. '+who),202

@api.get('/metricas')
@require_auth()
def metrics():
    def selected(m):
        result=metric_dict(m)
        kind=request.args.get('tipo')
        if kind in ('perda_pacotes','disponibilidade'): result.pop('latencia_ms')
        if kind in ('latencia','disponibilidade'): result.pop('perda_pacotes_pct')
        return result
    return jsonify(paginate(metric_query().order_by(Metrica.coletada_em,Metrica.id),selected))

@api.get('/metricas/<int:id>')
@require_auth()
def metric(id):
    m=db.session.scalar(select(Metrica).join(Dispositivo).where(Metrica.id==id,Dispositivo.empresa_id==g.user.empresa_id))
    if not m: raise NotFound('Métrica não encontrada.')
    return jsonify(metric_dict(m))

@api.get('/falhas')
@require_auth()
def failures():
    return jsonify(paginate(failure_query().order_by(Falha.inicio.desc(),Falha.id.desc()),failure_dict))

@api.get('/falhas/<int:id>')
@require_auth()
def failure(id):
    return jsonify(failure_dict(management.scoped_failure(id),True))

@api.put('/falhas/<int:id>/impacto')
@require_auth()
def update_impact(id):
    failure=management.scoped_failure(id)
    # usuarios_afetados empty/null: the device's people are used in the estimate.
    data=v.payload(['usuarios_afetados','observacao','custos_diretos'])
    impact=db.session.scalar(select(Impacto).where(Impacto.falha_id==failure.id))
    if not impact:
        impact=Impacto(falha_id=failure.id)
        db.session.add(impact)
    if 'usuarios_afetados' in data:
        impact.usuarios_afetados=v.optional(data['usuarios_afetados'],v.integer,'Usuários afetados')
        impact.origem='INFORMADO_PELO_USUARIO' if impact.usuarios_afetados is not None else 'NAO_INFORMADO'
    if 'custos_diretos' in data:
        impact.custos_diretos=v.optional(data['custos_diretos'],v.decimal_value,'Custos diretos')
    if 'observacao' in data:
        impact.observacao=v.string(data.get('observacao') or '','Observação',500,0)
    impact.atualizado_em=utcnow()
    db.session.flush()
    refresh_company(g.user.empresa_id,extra_failure=failure)
    db.session.commit()
    return jsonify(failure_dict(failure,True))

@api.get('/diagnosticos/<int:id>')
@require_auth()
def diagnostic(id):
    diag=db.session.scalar(select(Diagnostico).join(Falha).join(Dispositivo).where(Diagnostico.id==id,Dispositivo.empresa_id==g.user.empresa_id))
    if not diag: raise NotFound('Diagnóstico não encontrado.')
    return jsonify(diagnostic_dict(diag))

@api.get('/recomendacoes')
@require_auth()
def recommendations():
    return jsonify([recommendation_dict(r) for r in db.session.scalars(select(Recomendacao).order_by(Recomendacao.regra,Recomendacao.id))])

@api.get('/dashboard')
@require_auth()
def dashboard_endpoint():
    return jsonify(dashboard())

@api.get('/coletores')
@require_auth()
def collectors():
    # Read-only for every member (needed to assign devices); management is admin-only.
    return jsonify([collectors_service.collector_dict(c) for c in db.session.scalars(
        select(Coletor).where(Coletor.empresa_id==g.user.empresa_id).order_by(Coletor.revogado_em.isnot(None),Coletor.nome,Coletor.id))])

@api.post('/coletores')
@require_auth(admin=True)
def create_collector():
    data=v.payload(['nome'],['nome'])
    c,token=collectors_service.create_collector(data['nome'])
    # The plain credential is returned only once and never stored.
    return jsonify(coletor=collectors_service.collector_dict(c),token=token),201

@api.post('/coletores/<int:id>/rotacionar')
@require_auth(admin=True)
def rotate_collector(id):
    v.payload([])
    c,token=collectors_service.rotate_collector(id)
    return jsonify(coletor=collectors_service.collector_dict(c),token=token)

@api.post('/coletores/<int:id>/revogar')
@require_auth(admin=True)
def revoke_collector(id):
    v.payload([])
    return jsonify(collectors_service.collector_dict(collectors_service.revoke_collector(id)))

@api.get('/coletor/configuracao')
@collectors_service.require_collector
def collector_config():
    return jsonify(collectors_service.collector_config())

@api.post('/coletor/heartbeat')
@collectors_service.require_collector
def collector_heartbeat():
    return jsonify(collectors_service.heartbeat(v.payload(['versao','fila_pendente','erro'])))

@api.post('/coletor/amostras')
@collectors_service.require_collector
def collector_samples():
    return jsonify(collectors_service.ingest(v.payload(['amostras','erros'])))

@api.get('/relatorios/exportar')
@require_auth()
def report():
    return send_file(export_report(),mimetype='application/zip',as_attachment=True,
                     download_name=f'edgehealth-{utcnow().strftime("%Y%m%d-%H%M%S")}.zip',max_age=0)
