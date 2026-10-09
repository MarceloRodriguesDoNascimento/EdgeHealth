"""Routes of the API: URL + HTTP method -> controller method (with its authentication)."""
from flask import Blueprint
from app.security import require_auth, require_collector
from .auth_controller import AuthController
from .coletor_api_controller import ColetorApiController
from .coletor_controller import ColetorController
from .dashboard_controller import DashboardController
from .diagnostico_controller import DiagnosticoController
from .dispositivo_controller import DispositivoController
from .empresa_controller import EmpresaController
from .falha_controller import FalhaController
from .health_controller import HealthController
from .metrica_controller import MetricaController
from .relatorio_controller import RelatorioController
from .usuario_controller import UsuarioController

api = Blueprint('api', __name__, url_prefix='/api')

publica = lambda fn: fn  # noqa: E731
sessao = require_auth()
sessao_sem_termos = require_auth(terms=False)
admin = require_auth(admin=True)

health = HealthController()
auth = AuthController()
empresa = EmpresaController()
usuario = UsuarioController()
dispositivo = DispositivoController()
metrica = MetricaController()
falha = FalhaController()
diagnostico = DiagnosticoController()
dashboard = DashboardController()
relatorio = RelatorioController()
coletor = ColetorController()
coletor_api = ColetorApiController()

# (rule, HTTP method, endpoint, access, controller method)
ROTAS = [
    ('/health', 'GET', 'health', publica, health.verificar),
    ('/termos', 'GET', 'terms_version', publica, auth.versao_termos),
    ('/auth/registro', 'POST', 'register', publica, auth.registrar),
    ('/auth/login', 'POST', 'authenticate', publica, auth.login),
    ('/auth/me', 'GET', 'me', sessao_sem_termos, auth.perfil),
    ('/auth/aceite-termos', 'POST', 'accept_terms', sessao_sem_termos, auth.aceitar_termos),
    ('/auth/logout', 'POST', 'logout', sessao_sem_termos, auth.logout),

    ('/empresa', 'GET', 'company', sessao, empresa.obter),
    ('/empresa', 'PUT', 'update_company', admin, empresa.atualizar),
    ('/empresa/custos', 'PUT', 'update_company_costs', admin, empresa.configurar_custos),
    ('/empresa/custos/pular', 'POST', 'skip_cost_assistant', admin, empresa.pular_assistente_custos),

    ('/usuarios', 'GET', 'users', admin, usuario.listar),
    ('/usuarios', 'POST', 'create_user', admin, usuario.cadastrar),
    ('/usuarios/<int:id>', 'PUT', 'update_user', admin, usuario.atualizar),

    ('/dispositivos', 'GET', 'devices', sessao, dispositivo.listar),
    ('/dispositivos/<int:id>', 'GET', 'device', sessao, dispositivo.obter),
    ('/dispositivos', 'POST', 'create_device', sessao, dispositivo.cadastrar),
    ('/dispositivos/<int:id>', 'PUT', 'update_device', sessao, dispositivo.atualizar),
    ('/dispositivos/impacto-padrao', 'GET', 'device_impact_default', sessao, dispositivo.impacto_padrao),
    ('/dispositivos/<int:id>', 'DELETE', 'archive_device', sessao, dispositivo.arquivar),
    ('/dispositivos/<int:id>/desarquivar', 'POST', 'restore_device', sessao, dispositivo.desarquivar),
    ('/dispositivos/<int:id>/coletas', 'POST', 'request_collection', sessao, dispositivo.solicitar_coleta),

    ('/metricas', 'GET', 'metrics', sessao, metrica.listar),
    ('/metricas/<int:id>', 'GET', 'metric', sessao, metrica.obter),

    ('/falhas', 'GET', 'failures', sessao, falha.listar),
    ('/falhas/<int:id>', 'GET', 'failure', sessao, falha.obter),
    ('/falhas/<int:id>/impacto', 'PUT', 'update_impact', sessao, falha.registrar_impacto),
    ('/falhas/<int:id>/explicacao-ia', 'POST', 'explain_failure_with_ai', sessao, falha.explicar_com_ia),

    ('/diagnosticos/<int:id>', 'GET', 'diagnostic', sessao, diagnostico.obter),
    ('/recomendacoes', 'GET', 'recommendations', sessao, diagnostico.listar_recomendacoes),

    ('/dashboard', 'GET', 'dashboard_endpoint', sessao, dashboard.obter),
    ('/relatorios/exportar', 'GET', 'report', sessao, relatorio.exportar),

    # Read-only for every member (needed to assign devices); management is admin-only.
    ('/coletores', 'GET', 'collectors', sessao, coletor.listar),
    ('/coletores', 'POST', 'create_collector', admin, coletor.cadastrar),
    ('/coletores/<int:id>/rotacionar', 'POST', 'rotate_collector', admin, coletor.rotacionar),
    ('/coletores/<int:id>/revogar', 'POST', 'revoke_collector', admin, coletor.revogar),

    ('/coletor/configuracao', 'GET', 'collector_config', require_collector, coletor_api.configuracao),
    ('/coletor/heartbeat', 'POST', 'collector_heartbeat', require_collector, coletor_api.heartbeat),
    ('/coletor/amostras', 'POST', 'collector_samples', require_collector, coletor_api.amostras),
]

for regra, metodo, endpoint, acesso, acao in ROTAS:
    api.add_url_rule(regra, endpoint=endpoint, view_func=acesso(acao), methods=[metodo])
