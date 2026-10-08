from flask import Blueprint, g, jsonify, request, current_app, send_file
from werkzeug.exceptions import BadRequest
from .security import require_auth, require_collector, set_session_cookies, clear_session_cookies
from services.autenticacao.aceitar_termos_service import AceitarTermosService
from services.autenticacao.autenticar_usuario_service import AutenticarUsuarioService
from services.autenticacao.consultar_termos_service import ConsultarTermosService
from services.autenticacao.encerrar_sessao_service import EncerrarSessaoService
from services.autenticacao.obter_perfil_service import ObterPerfilService
from services.coletor_api.obter_configuracao_coletor_service import ObterConfiguracaoColetorService
from services.coletor_api.receber_amostras_service import ReceberAmostrasService
from services.coletor_api.registrar_heartbeat_service import RegistrarHeartbeatService
from services.coletores.cadastrar_coletor_service import CadastrarColetorService
from services.coletores.listar_coletores_service import ListarColetoresService
from services.coletores.revogar_coletor_service import RevogarColetorService
from services.coletores.rotacionar_credencial_coletor_service import RotacionarCredencialColetorService
from services.dashboard.gerar_dashboard_service import GerarDashboardService
from services.diagnosticos.listar_recomendacoes_service import ListarRecomendacoesService
from services.diagnosticos.obter_diagnostico_service import ObterDiagnosticoService
from services.dispositivos.arquivar_dispositivo_service import ArquivarDispositivoService
from services.dispositivos.atualizar_dispositivo_service import AtualizarDispositivoService
from services.dispositivos.cadastrar_dispositivo_service import CadastrarDispositivoService
from services.dispositivos.desarquivar_dispositivo_service import DesarquivarDispositivoService
from services.dispositivos.listar_dispositivos_service import ListarDispositivosService
from services.dispositivos.obter_dispositivo_service import ObterDispositivoService
from services.dispositivos.obter_impacto_padrao_service import ObterImpactoPadraoService
from services.dispositivos.solicitar_coleta_service import SolicitarColetaService
from services.empresas.atualizar_empresa_service import AtualizarEmpresaService
from services.empresas.configurar_custos_service import ConfigurarCustosService
from services.empresas.obter_empresa_service import ObterEmpresaService
from services.empresas.pular_assistente_custos_service import PularAssistenteCustosService
from services.empresas.registrar_empresa_service import RegistrarEmpresaService
from services.falhas.listar_falhas_service import ListarFalhasService
from services.falhas.obter_falha_service import ObterFalhaService
from services.falhas.registrar_impacto_service import RegistrarImpactoService
from services.metricas.listar_metricas_service import ListarMetricasService
from services.metricas.obter_metrica_service import ObterMetricaService
from services.relatorios.exportar_relatorio_service import ExportarRelatorioService
from services.saude.verificar_saude_service import VerificarSaudeService
from services.usuarios.atualizar_usuario_service import AtualizarUsuarioService
from services.usuarios.cadastrar_usuario_service import CadastrarUsuarioService
from services.usuarios.listar_usuarios_service import ListarUsuariosService

api=Blueprint('api',__name__,url_prefix='/api')
DEVICE_FIELDS=['nome','ip','tipo','localizacao','coletor_id','usuarios_dependentes','perda_produtividade_pct','receita_hora_dependente']

def payload(allowed, required=()):
    if not request.is_json:
        raise BadRequest('Envie um objeto JSON.')
    data = request.get_json()
    if not isinstance(data, dict):
        raise BadRequest('Envie um objeto JSON.')
    unknown = set(data) - set(allowed)
    if unknown:
        raise BadRequest('Campos não permitidos: ' + ', '.join(sorted(unknown)))
    for field in required:
        if field not in data or data[field] is None or data[field] == '':
            raise BadRequest(f'O campo {field} é obrigatório.')
    return data

def session_response(result,status=200):
    response=jsonify(result.corpo)
    response.status_code=status
    return set_session_cookies(response,result.token,result.csrf)

@api.get('/health')
def health():
    body,ready=VerificarSaudeService().executar()
    return jsonify(body),200 if ready else 503

@api.get('/termos')
def terms_version():
    return jsonify(ConsultarTermosService().executar())

@api.post('/auth/registro')
def register():
    return session_response(RegistrarEmpresaService().executar(payload(['nome_fantasia','cnpj','telefone','nome','email','senha','aceite_termos'],['nome_fantasia','cnpj','nome','email','senha'])),201)

@api.post('/auth/login')
def authenticate():
    data=payload(['email','senha'],['email','senha'])
    return session_response(AutenticarUsuarioService().executar(data['email'],data['senha'],request.remote_addr))

@api.get('/auth/me')
@require_auth(terms=False)
def me():
    return jsonify(ObterPerfilService().executar(g.user))

@api.post('/auth/aceite-termos')
@require_auth(terms=False)
def accept_terms():
    return jsonify(AceitarTermosService().executar(g.user,payload(['aceite_termos'],['aceite_termos'])['aceite_termos']))

@api.post('/auth/logout')
@require_auth(terms=False)
def logout():
    EncerrarSessaoService().executar(g.auth_session)
    return clear_session_cookies(current_app.response_class(status=204))

@api.get('/empresa')
@require_auth()
def company():
    return jsonify(ObterEmpresaService().executar(g.user.empresa_id))

@api.put('/empresa')
@require_auth(admin=True)
def update_company():
    return jsonify(AtualizarEmpresaService().executar(g.user.empresa_id,payload(['nome_fantasia','cnpj','email','telefone'])))

@api.put('/empresa/custos')
@require_auth(admin=True)
def update_company_costs():
    return jsonify(ConfigurarCustosService().executar(g.user.empresa_id,payload(['salario_medio','fator_encargos','horas_mes','total_funcionarios','expediente','fuso'])))

@api.post('/empresa/custos/pular')
@require_auth(admin=True)
def skip_cost_assistant():
    payload([])
    return jsonify(PularAssistenteCustosService().executar(g.user.empresa_id))

@api.get('/usuarios')
@require_auth(admin=True)
def users():
    return jsonify(ListarUsuariosService().executar(g.user.empresa_id))

@api.post('/usuarios')
@require_auth(admin=True)
def create_user():
    return jsonify(CadastrarUsuarioService().executar(g.user,payload(['nome','email','senha','papel'],['nome','email','senha']))),201

@api.put('/usuarios/<int:id>')
@require_auth(admin=True)
def update_user(id):
    return jsonify(AtualizarUsuarioService().executar(g.user,id,payload(['nome','email','senha','papel','ativo'])))

@api.get('/dispositivos')
@require_auth()
def devices():
    return jsonify(ListarDispositivosService().executar(g.user.empresa_id,request.args.get('arquivados','0')))

@api.get('/dispositivos/<int:id>')
@require_auth()
def device(id):
    return jsonify(ObterDispositivoService().executar(g.user.empresa_id,id))

@api.post('/dispositivos')
@require_auth()
def create_device():
    return jsonify(CadastrarDispositivoService().executar(g.user.empresa_id,payload(DEVICE_FIELDS,['nome','ip','tipo','localizacao']))),201

@api.put('/dispositivos/<int:id>')
@require_auth()
def update_device(id):
    return jsonify(AtualizarDispositivoService().executar(g.user.empresa_id,id,payload(DEVICE_FIELDS)))

@api.get('/dispositivos/impacto-padrao')
@require_auth()
def device_impact_default():
    return jsonify(ObterImpactoPadraoService().executar(g.user.empresa_id,request.args.get('tipo','')))

@api.delete('/dispositivos/<int:id>')
@require_auth()
def archive_device(id):
    ArquivarDispositivoService().executar(g.user.empresa_id,id)
    return '',204

@api.post('/dispositivos/<int:id>/desarquivar')
@require_auth()
def restore_device(id):
    payload([])
    return jsonify(DesarquivarDispositivoService().executar(g.user.empresa_id,id))

@api.post('/dispositivos/<int:id>/coletas')
@require_auth()
def request_collection(id):
    payload([])
    return jsonify(SolicitarColetaService().executar(g.user.empresa_id,id)),202

@api.get('/metricas')
@require_auth()
def metrics():
    a=request.args
    return jsonify(ListarMetricasService().executar(g.user.empresa_id,a.get('dispositivo_id'),a.get('tipo'),a.get('inicio'),a.get('fim'),a.get('pagina'),a.get('limite')))

@api.get('/metricas/<int:id>')
@require_auth()
def metric(id):
    return jsonify(ObterMetricaService().executar(g.user.empresa_id,id))

@api.get('/falhas')
@require_auth()
def failures():
    a=request.args
    return jsonify(ListarFalhasService().executar(g.user.empresa_id,a.get('dispositivo_id'),a.get('severidade'),a.get('estado'),a.get('inicio'),a.get('fim'),a.get('pagina'),a.get('limite')))

@api.get('/falhas/<int:id>')
@require_auth()
def failure(id):
    return jsonify(ObterFalhaService().executar(g.user.empresa_id,id))

@api.put('/falhas/<int:id>/impacto')
@require_auth()
def update_impact(id):
    found=ObterFalhaService().buscar(g.user.empresa_id,id)
    return jsonify(RegistrarImpactoService().executar(g.user.empresa_id,found,payload(['usuarios_afetados','observacao','custos_diretos'])))

@api.get('/diagnosticos/<int:id>')
@require_auth()
def diagnostic(id):
    return jsonify(ObterDiagnosticoService().executar(g.user.empresa_id,id))

@api.get('/recomendacoes')
@require_auth()
def recommendations():
    return jsonify(ListarRecomendacoesService().executar())

@api.get('/dashboard')
@require_auth()
def dashboard_endpoint():
    a=request.args
    return jsonify(GerarDashboardService().executar(g.user.empresa_id,a.get('dispositivo_id'),a.get('inicio'),a.get('fim')))

@api.get('/coletores')
@require_auth()
def collectors():
    return jsonify(ListarColetoresService().executar(g.user.empresa_id))

@api.post('/coletores')
@require_auth(admin=True)
def create_collector():
    return jsonify(CadastrarColetorService().executar(g.user.empresa_id,payload(['nome'],['nome'])['nome'])),201

@api.post('/coletores/<int:id>/rotacionar')
@require_auth(admin=True)
def rotate_collector(id):
    payload([])
    return jsonify(RotacionarCredencialColetorService().executar(g.user.empresa_id,id))

@api.post('/coletores/<int:id>/revogar')
@require_auth(admin=True)
def revoke_collector(id):
    payload([])
    return jsonify(RevogarColetorService().executar(g.user.empresa_id,id))

@api.get('/coletor/configuracao')
@require_collector
def collector_config():
    return jsonify(ObterConfiguracaoColetorService().executar(g.collector))

@api.post('/coletor/heartbeat')
@require_collector
def collector_heartbeat():
    return jsonify(RegistrarHeartbeatService().executar(g.collector,payload(['versao','fila_pendente','erro'])))

@api.post('/coletor/amostras')
@require_collector
def collector_samples():
    return jsonify(ReceberAmostrasService().executar(g.collector,payload(['amostras','erros'])))

@api.get('/relatorios/exportar')
@require_auth()
def report():
    a=request.args
    file,name=ExportarRelatorioService().executar(g.user.empresa_id,a.get('dispositivo_id'),a.get('inicio'),a.get('fim'))
    return send_file(file,mimetype='application/zip',as_attachment=True,download_name=name,max_age=0)
