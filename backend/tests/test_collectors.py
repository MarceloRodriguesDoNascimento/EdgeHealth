import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from sqlalchemy import select, func
from app import db
from app.models import Coletor, Dispositivo, Metrica, Falha, utcnow
from app.services.monitoring import ProbeResult, run_cycle
from conftest import register, auth_headers


def stamp(seconds_ago=0):
    return (utcnow() - timedelta(seconds=seconds_ago)).isoformat() + 'Z'


def sample(device_id, sent=4, received=4, latency=2.0, seconds_ago=0, uid=None):
    return dict(id=uid or str(uuid.uuid4()), dispositivo_id=device_id, coletada_em=stamp(seconds_ago),
                enviados=sent, recebidos=received, latencia_ms=latency if received else None)


def bearer(token):
    return {'Authorization': 'Bearer ' + token}


def new_collector(client, name='Coletor matriz'):
    response = client.post('/api/coletores', json={'nome': name}, headers=auth_headers(client))
    assert response.status_code == 201, response.json
    return response.json['coletor'], response.json['token']


def assign(client, device_id, collector_id):
    response = client.put(f'/api/dispositivos/{device_id}', json={'coletor_id': collector_id}, headers=auth_headers(client))
    assert response.status_code == 200, response.json
    return response.json


def send(client, token, samples=(), errors=()):
    return client.post('/api/coletor/amostras', json={'amostras': list(samples), 'erros': list(errors)}, headers=bearer(token))


def test_credentials_are_hashed_rotated_and_revoked(app, signed):
    collector, token = new_collector(signed)
    assert token.startswith('ehc_') and collector['token_prefixo'] == token[:12]
    assert collector['estado'] == 'NUNCA_CONECTADO'
    with app.app_context():
        stored = db.session.get(Coletor, collector['id'])
        assert token not in (stored.token_hash, stored.token_prefixo)
    assert 'token' not in signed.get('/api/coletores').json[0]
    client = app.test_client()
    assert client.get('/api/coletor/configuracao').status_code == 401
    assert client.get('/api/coletor/configuracao', headers=bearer('ehc_invalid')).status_code == 401
    # A user session cookie is not a collector credential.
    assert signed.get('/api/coletor/configuracao').status_code == 401
    assert client.get('/api/coletor/configuracao', headers=bearer(token)).status_code == 200
    rotated = signed.post(f'/api/coletores/{collector["id"]}/rotacionar', json={}, headers=auth_headers(signed)).json
    assert client.get('/api/coletor/configuracao', headers=bearer(token)).status_code == 401
    assert client.get('/api/coletor/configuracao', headers=bearer(rotated['token'])).status_code == 200
    assert signed.post(f'/api/coletores/{collector["id"]}/revogar', json={}, headers=auth_headers(signed)).json['estado'] == 'REVOGADO'
    assert client.get('/api/coletor/configuracao', headers=bearer(rotated['token'])).status_code == 401
    assert signed.post(f'/api/coletores/{collector["id"]}/rotacionar', json={}, headers=auth_headers(signed)).status_code == 409


def test_only_admins_manage_collectors_and_tenants_are_isolated(app, signed, device):
    h = auth_headers(signed)
    signed.post('/api/usuarios', json={'nome': 'Tec', 'email': 'tec@a.example', 'senha': 'senha-tecnico-1', 'papel': 'TECNICO'}, headers=h)
    tech = app.test_client()
    tech.post('/api/auth/login', json={'email': 'tec@a.example', 'senha': 'senha-tecnico-1'})
    tech.post('/api/auth/aceite-termos', json={'aceite_termos': True}, headers=auth_headers(tech))
    assert tech.post('/api/coletores', json={'nome': 'x'}, headers=auth_headers(tech)).status_code == 403
    assert tech.get('/api/coletores').status_code == 200  # read-only list, never the credential
    collector_a, token_a = new_collector(signed)
    other = app.test_client()
    assert register(other, email='admin@b.example', cnpj='11444777000161', name='Empresa B').status_code == 201
    collector_b, token_b = new_collector(other, 'Coletor B')
    device_b = other.post('/api/dispositivos', json={'nome': 'B', 'ip': '10.0.0.2', 'tipo': 'Switch', 'localizacao': 'B'}, headers=auth_headers(other)).json
    # A company cannot assign, rotate, revoke or see another company's collector.
    assert signed.put(f'/api/dispositivos/{device["id"]}', json={'coletor_id': collector_b['id']}, headers=h).status_code == 404
    assert signed.post(f'/api/coletores/{collector_b["id"]}/revogar', json={}, headers=h).status_code == 404
    assert [c['id'] for c in signed.get('/api/coletores').json] == [collector_a['id']]
    assign(signed, device['id'], collector_a['id'])
    assign(other, device_b['id'], collector_b['id'])
    config = app.test_client().get('/api/coletor/configuracao', headers=bearer(token_a)).json
    assert [d['id'] for d in config['dispositivos']] == [device['id']]
    # Collector A cannot write samples or errors for company B's device.
    result = send(app.test_client(), token_a, [sample(device_b['id'])]).json
    assert result['resultados'][0]['resultado'] == 'REJEITADA'
    assert send(app.test_client(), token_a, errors=[{'dispositivo_id': device_b['id'], 'tipo': 'FALHA_COLETOR'}]).status_code == 400
    assert send(app.test_client(), token_a, [dict(sample(device['id']), empresa_id=2)]).json['resultados'][0]['resultado'] == 'REJEITADA'
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 0


def test_ingestion_runs_full_incident_lifecycle_without_duplicates(app, signed, device):
    collector, token = new_collector(signed)
    assign(signed, device['id'], collector['id'])
    client = app.test_client()
    first = sample(device['id'], seconds_ago=100)
    assert send(client, token, [first]).json['resultados'][0]['resultado'] == 'ACEITA'
    # Resending the same batch after a lost response is idempotent.
    assert send(client, token, [first]).json['resultados'][0]['resultado'] == 'DUPLICADA'
    outage = [sample(device['id'], received=0, seconds_ago=90 - i * 10) for i in range(4)]
    results = send(client, token, outage + [outage[0]]).json['resultados']
    assert [r['resultado'] for r in results].count('ACEITA') == 4
    with app.app_context():
        assert db.session.get(Dispositivo, device['id']).status == 'OFFLINE'
        assert db.session.scalar(select(func.count()).select_from(Falha)) == 1
        failure = db.session.scalar(select(Falha))
        assert failure.tipo == 'INDISPONIBILIDADE' and failure.estado == 'ABERTA'
    recovery = [sample(device['id'], seconds_ago=40), sample(device['id'], seconds_ago=30)]
    send(client, token, recovery)
    with app.app_context():
        failure = db.session.scalar(select(Falha))
        assert failure.estado == 'ENCERRADA' and failure.encerramento == 'RECUPERACAO'
        metric = db.session.scalar(select(Metrica).where(Metrica.amostra_uid == first['id']))
        assert metric.coletor_id == collector['id'] and metric.recebida_em and metric.latencia_ms == 2.0
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 7
    # A delayed sample from the outage window is kept as history but cannot reopen the incident.
    late = send(client, token, [sample(device['id'], received=0, seconds_ago=95)]).json['resultados'][0]
    assert late['resultado'] == 'ATRASADA'
    with app.app_context():
        assert db.session.get(Dispositivo, device['id']).status == 'ONLINE'
        assert db.session.scalar(select(func.count()).select_from(Falha)) == 1
        assert db.session.scalar(select(Metrica).where(Metrica.fora_de_ordem.is_(True))).status == 'OFFLINE'
    page = signed.get(f'/api/metricas?dispositivo_id={device["id"]}').json
    assert page['total'] == 8 and any(m['fora_de_ordem'] for m in page['items'])


def test_invalid_samples_are_rejected_individually(app, signed, device):
    collector, token = new_collector(signed)
    assign(signed, device['id'], collector['id'])
    bad = [
        dict(sample(device['id']), recebidos=5),
        dict(sample(device['id']), recebidos=0, latencia_ms=0),
        dict(sample(device['id']), latencia_ms=None),
        dict(sample(device['id']), coletada_em=stamp(-3600)),
        dict(sample(device['id']), coletada_em=stamp(3 * 86400)),
        dict(sample(device['id']), coletada_em=utcnow().isoformat()),
        dict(sample(device['id']), id='not-a-uuid'),
        dict(sample(device['id']), status='ONLINE'),
        dict(sample(device['id']), enviados=True),
    ]
    good = sample(device['id'])
    result = send(app.test_client(), token, bad + [good]).json['resultados']
    assert [r['resultado'] for r in result] == ['REJEITADA'] * len(bad) + ['ACEITA']
    big = [sample(device['id']) for _ in range(app.config['COLLECTOR_MAX_BATCH'] + 1)]
    assert send(app.test_client(), token, big).status_code == 400


def test_collector_problems_are_not_device_failures(app, signed, device):
    collector, token = new_collector(signed)
    assign(signed, device['id'], collector['id'])
    client = app.test_client()
    error = {'dispositivo_id': device['id'], 'tipo': 'PERMISSAO_ICMP', 'mensagem': 'Operation not permitted'}
    assert send(client, token, errors=[error]).status_code == 200
    beat = client.post('/api/coletor/heartbeat', json={'versao': '1.0.0', 'fila_pendente': 3}, headers=bearer(token))
    assert beat.status_code == 200 and beat.json['estado'] == 'ATIVO'
    listed = signed.get('/api/dispositivos').json[0]
    assert listed['status'] is None and 'ICMP' in listed['erro_coleta'] and listed['coletor_estado'] == 'ATIVO'
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 0
        assert db.session.scalar(select(func.count()).select_from(Falha)) == 0
        c = db.session.get(Coletor, collector['id'])
        assert c.versao == '1.0.0' and c.fila_pendente == 3
        c.ultimo_contato = utcnow() - timedelta(seconds=app.config['COLLECTOR_STALE_SECONDS'] + 1)
        db.session.commit()
    # A silent collector is reported as stale; it does not fabricate OFFLINE devices.
    dashboard = signed.get('/api/dashboard').json
    assert dashboard['coletores'][0]['estado'] == 'DESATUALIZADO'
    assert dashboard['indicadores']['offline'] == 0 and dashboard['indicadores']['falhas_abertas'] == 0
    assert client.post('/api/coletor/heartbeat', json={'erro': {'tipo': 'OUTRO'}}, headers=bearer(token)).status_code == 400


def test_local_worker_never_probes_remote_devices(app, signed, device):
    collector, _ = new_collector(signed)
    assign(signed, device['id'], collector['id'])
    assert run_cycle(app, lambda *_: ProbeResult(4, 4, 1)) == 0
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 0
    assert signed.post(f'/api/dispositivos/{device["id"]}/coletas', json={}, headers=auth_headers(signed)).status_code == 202
    assign(signed, device['id'], None)
    assert run_cycle(app, lambda *_: ProbeResult(4, 4, 1)) == 1


def test_rate_limit_and_concurrent_resend(app, signed, device):
    collector, token = new_collector(signed)
    assign(signed, device['id'], collector['id'])
    batch = [sample(device['id'], seconds_ago=30 - i) for i in range(5)]

    def post(_):
        return send(app.test_client(), token, batch).json['resultados']

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = [r['resultado'] for rs in pool.map(post, range(4)) for r in rs]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 5
    assert outcomes.count('ACEITA') == 5
    assert set(outcomes) <= {'ACEITA', 'DUPLICADA', 'TENTAR_NOVAMENTE'}
    app.config['COLLECTOR_MAX_REQUESTS_PER_MINUTE'] = 1
    with app.app_context():
        c = db.session.get(Coletor, collector['id'])
        c.janela_inicio, c.janela_requisicoes = utcnow(), 0
        db.session.commit()
    client = app.test_client()
    assert client.get('/api/coletor/configuracao', headers=bearer(token)).status_code == 200
    assert client.get('/api/coletor/configuracao', headers=bearer(token)).status_code == 429
