from flask import Blueprint, g, jsonify, request, current_app, send_file
from pathlib import Path
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import select, text, inspect
from werkzeug.exceptions import BadRequest, NotFound, Conflict
from .extensions import db
from .models import Empresa, Usuario, Dispositivo, Metrica, Falha, Impacto, Diagnostico, Recomendacao, utcnow
from . import validation as v
from .services import management as management
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

@api.post('/auth/registro')
def register():
    data=v.payload(['nome_fantasia','cnpj','telefone','nome','email','senha'],['nome_fantasia','cnpj','nome','email','senha'])
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
@require_auth()
def me():
    return jsonify(usuario=user_dict(g.user),empresa=company_dict(db.session.get(Empresa,g.user.empresa_id)))

@api.post('/auth/logout')
@require_auth()
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
    return jsonify(device_dict(management.save_device(v.payload(['nome','ip','tipo','localizacao'],['nome','ip','tipo','localizacao'])))),201

@api.put('/dispositivos/<int:id>')
@require_auth()
def update_device(id):
    return jsonify(device_dict(management.save_device(v.payload(['nome','ip','tipo','localizacao']),id)))

@api.delete('/dispositivos/<int:id>')
@require_auth()
def archive_device(id):
    management.archive_device(id)
    return '',204

@api.post('/dispositivos/<int:id>/coletas')
@require_auth()
def request_collection(id):
    v.payload([])
    d=management.scoped_device(id,False)
    if d.lease_until and d.lease_until>utcnow(): raise Conflict('Uma coleta já está em andamento.')
    d.proxima_coleta=utcnow()
    db.session.commit()
    return jsonify(mensagem='Coleta solicitada. O worker a executará no próximo ciclo.'),202

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
    data=v.payload(['usuarios_afetados','observacao'],['usuarios_afetados'])
    count=v.integer(data['usuarios_afetados'],'Usuários afetados')
    impact=db.session.scalar(select(Impacto).where(Impacto.falha_id==failure.id))
    if not impact:
        impact=Impacto(falha_id=failure.id)
        db.session.add(impact)
    impact.usuarios_afetados=count
    impact.origem='INFORMADO_PELO_USUARIO'
    impact.observacao=v.string(data.get('observacao',''),'Observação',500,0)
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

@api.get('/relatorios/exportar')
@require_auth()
def report():
    return send_file(export_report(),mimetype='application/zip',as_attachment=True,
                     download_name=f'edgehealth-{utcnow().strftime("%Y%m%d-%H%M%S")}.zip',max_age=0)
