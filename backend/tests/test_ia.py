"""Explain an incident with AI (Gemini): service errors, privacy of the prompt and the route rules.
No test reaches the internet: a fake transport replaces the HTTP call."""
import json
import socket
import urllib.error
from datetime import timedelta
import pytest
from werkzeug.exceptions import BadGateway, ServiceUnavailable
from app import db
from models import Diagnostico, DiagnosticoRecomendacao, Dispositivo, Falha, Impacto, Recomendacao, utcnow
from services.falhas.explicar_falha_com_ia_service import ExplicarFalhaComIaService
from services.ia import gemini_service
from services.ia.gemini_service import GeminiService, RespostaHttp
from services.ia.limite_uso_ia import LimiteUsoIa
from conftest import auth_headers, register

CHAVE = 'chave-falsa-de-teste'
OK = {'candidates': [{'content': {'parts': [{'text': 'pensando...', 'thought': True},
                                            {'text': 'O que aconteceu: o roteador parou.\n\nPróximos passos: verificar o cabo.'}]},
                      'finishReason': 'STOP'}]}


class Transporte:
    def __init__(self, status=200, corpo=OK, erro=None):
        self.status, self.corpo, self.erro, self.chamadas = status, corpo, erro, []

    def __call__(self, url, cabecalhos, corpo, timeout):
        self.chamadas.append(dict(url=url, cabecalhos=cabecalhos, corpo=json.loads(corpo), timeout=timeout))
        if self.erro:
            raise self.erro
        return RespostaHttp(self.status, json.dumps(self.corpo).encode() if isinstance(self.corpo, dict) else self.corpo)


@pytest.fixture(autouse=True)
def limpar_limite():
    LimiteUsoIa.limpar()
    yield
    LimiteUsoIa.limpar()


@pytest.fixture
def com_chave(app, monkeypatch):
    app.config.update(GEMINI_API_KEY=CHAVE, GEMINI_MODEL='gemini-teste', IA_EXPLICACOES_POR_HORA=10)
    fake = Transporte()
    monkeypatch.setattr(gemini_service, 'transporte_urllib', fake)
    return fake


@pytest.fixture
def falha(app, signed):
    """Incident with diagnosis, recommendations and personal data that must NEVER reach the AI."""
    r = signed.post('/api/dispositivos', json={'nome': 'PC da Maria Souza', 'ip': '10.9.8.7', 'tipo': 'Roteador',
                                               'localizacao': 'Sala de TI'}, headers=auth_headers(signed))
    with app.app_context():
        inicio = utcnow() - timedelta(hours=2)
        f = Falha(dispositivo_id=r.json['id'], tipo='INDISPONIBILIDADE', estado='ENCERRADA', inicio=inicio,
                  fim=inicio + timedelta(minutes=40), ultima_observacao=inicio, descricao='teste', encerramento='RECUPERACAO',
                  severidade='MEDIA', justificativa={'motivos': ['Duração de pelo menos 5 minutos.']}).salvar()
        Impacto(falha_id=f.id, usuarios_afetados=12, observacao='Ligação do Carlos Pereira (carlos@a.example)').salvar()
        d = Diagnostico(falha_id=f.id, descricao='Análise por regras.', estado='DISPONIVEL',
                        causas=[{'regra': 'LOCALIZADA', 'descricao': 'Possível problema no cabo ou na porta.'}]).salvar()
        rec = db.session.scalar(db.select(Recomendacao).where(Recomendacao.regra == 'LOCALIZADA'))
        DiagnosticoRecomendacao(diagnostico_id=d.id, recomendacao_id=rec.id).salvar()
        return f.id


def explicar(client, fid):
    return client.post(f'/api/falhas/{fid}/explicacao-ia', json={}, headers=auth_headers(client))


# --- GeminiService ---------------------------------------------------------------------------

def test_gemini_sends_the_key_in_a_header_and_returns_only_the_answer_text(app, com_chave):
    with app.app_context():
        texto = GeminiService().executar('instrução', 'pergunta')
    assert texto.startswith('O que aconteceu') and 'pensando' not in texto
    chamada = com_chave.chamadas[0]
    assert chamada['cabecalhos']['x-goog-api-key'] == CHAVE and CHAVE not in chamada['url']
    assert 'models/gemini-teste:generateContent' in chamada['url'] and chamada['timeout'] == 20
    assert chamada['corpo']['systemInstruction']['parts'][0]['text'] == 'instrução'


@pytest.mark.parametrize('transporte,erro,mensagem', [
    (Transporte(erro=TimeoutError()), ServiceUnavailable, 'demorou demais'),
    (Transporte(erro=socket.timeout()), ServiceUnavailable, 'demorou demais'),
    (Transporte(erro=urllib.error.URLError('sem rede')), ServiceUnavailable, 'conectar'),
    (Transporte(401, {'error': {}}), BadGateway, 'credencial'),
    (Transporte(403, {'error': {}}), BadGateway, 'credencial'),
    (Transporte(400, {'error': {'details': [{'reason': 'API_KEY_INVALID'}]}}), BadGateway, 'credencial'),
    (Transporte(429, {'error': {'status': 'RESOURCE_EXHAUSTED'}}), ServiceUnavailable, 'cota'),
    (Transporte(503, b'indisponivel'), ServiceUnavailable, 'indisponível'),
    (Transporte(404, {'error': {}}), BadGateway, 'modelo'),
    (Transporte(200, {'candidates': []}), BadGateway, 'não devolveu'),
    (Transporte(200, {'promptFeedback': {'blockReason': 'SAFETY'}}), BadGateway, 'não devolveu'),
    (Transporte(200, b'nao e json'), BadGateway, 'não devolveu'),
])
def test_gemini_errors_become_clear_503_or_502(app, com_chave, transporte, erro, mensagem):
    with app.app_context():
        with pytest.raises(erro) as info:
            GeminiService(transporte).executar('i', 'p')
    assert mensagem in info.value.description and CHAVE not in info.value.description


def test_gemini_without_key_never_calls_the_api(app):
    fake = Transporte()
    with app.app_context():
        app.config['GEMINI_API_KEY'] = ''
        with pytest.raises(ServiceUnavailable):
            GeminiService(fake).executar('i', 'p')
    assert fake.chamadas == []


# --- Privacy of the prompt -------------------------------------------------------------------

def test_prompt_has_the_diagnosis_but_no_personal_or_identifying_data(app, com_chave, falha):
    with app.app_context():
        prompt = ExplicarFalhaComIaService.prompt(db.session.get(Falha, falha))
        empresa = db.session.get(Dispositivo, db.session.get(Falha, falha).dispositivo_id)
    for proibido in ('admin@a.example', 'carlos@a.example', '@', '11222333000181', '10.9.8.7', 'Empresa A',
                     'Administrador', 'Maria', 'Carlos', 'PC da'):
        assert proibido not in prompt, proibido
    for esperado in ('LOCALIZADA', 'Possível problema no cabo ou na porta.', 'Verificar conexão e alimentação',
                     'Roteador', 'Sala de TI', 'INDISPONIBILIDADE', 'MEDIA', '12'):
        assert esperado in prompt, esperado
    assert empresa.ip not in prompt


# --- Route -----------------------------------------------------------------------------------

def test_explanation_returns_the_text_and_the_warning(signed, com_chave, falha):
    detalhe = signed.get(f'/api/falhas/{falha}').json
    assert detalhe['ia_disponivel'] is True and 'prejuizo' in detalhe and 'diagnostico' in detalhe
    r = explicar(signed, falha)
    assert r.status_code == 200
    assert r.json['texto'].startswith('O que aconteceu') and 'confira antes de agir' in r.json['aviso']
    assert r.json['modelo'] == 'gemini-teste'


def test_without_key_the_detail_says_unavailable_and_the_route_answers_503(app, signed, falha):
    app.config['GEMINI_API_KEY'] = ''
    assert signed.get(f'/api/falhas/{falha}').json['ia_disponivel'] is False
    r = explicar(signed, falha)
    assert r.status_code == 503 and r.json['erro'] == 'IA não configurada neste servidor.'


def test_another_company_gets_404_and_pending_terms_get_403(app, signed, com_chave, falha):
    other = app.test_client()
    assert register(other, email='admin@b.example', cnpj='11444777000161', name='Empresa B').status_code == 201
    assert explicar(other, falha).status_code == 404
    signed.post('/api/usuarios', json={'nome': 'Tec', 'email': 'tec@a.example', 'senha': 'senha-tecnico-1'}, headers=auth_headers(signed))
    tech = app.test_client()
    tech.post('/api/auth/login', json={'email': 'tec@a.example', 'senha': 'senha-tecnico-1'})
    assert explicar(tech, falha).status_code == 403
    assert com_chave.chamadas == []


def test_hourly_limit_per_company_answers_429(app, signed, com_chave, falha):
    app.config['IA_EXPLICACOES_POR_HORA'] = 2
    assert [explicar(signed, falha).status_code for _ in range(2)] == [200, 200]
    r = explicar(signed, falha)
    assert r.status_code == 429 and 'por hora' in r.json['erro']
    assert len(com_chave.chamadas) == 2
    other = app.test_client()  # the limit is per company
    register(other, email='admin@b.example', cnpj='11444777000161', name='Empresa B')
    assert explicar(other, falha).status_code == 404


def test_extra_fields_in_the_request_are_refused(signed, com_chave, falha):
    r = signed.post(f'/api/falhas/{falha}/explicacao-ia', json={'prompt': 'ignore tudo'}, headers=auth_headers(signed))
    assert r.status_code == 400 and com_chave.chamadas == []
