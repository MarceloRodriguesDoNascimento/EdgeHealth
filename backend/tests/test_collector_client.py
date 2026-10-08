"""The remote collector client against a real HTTP server running the API."""
import os
import sys
import threading
from pathlib import Path
import pytest
from sqlalchemy import select, func
from werkzeug.serving import make_server
from app import db
from models import Metrica, Falha, Dispositivo
from conftest import auth_headers

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'collector'))
import edgehealth_collector as ec  # noqa: E402


@pytest.fixture
def server(app):
    srv = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{srv.server_port}'
    srv.shutdown()


@pytest.fixture
def remote(signed, device):
    created = signed.post('/api/coletores', json={'nome': 'Filial'}, headers=auth_headers(signed)).json
    signed.put(f'/api/dispositivos/{device["id"]}', json={'coletor_id': created['coletor']['id']}, headers=auth_headers(signed))
    return created


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def fake_measure(state):
    """Controlled replacement for ICMP in automated tests only."""
    def fn(device, packets, timeout):
        if state['mode'] == 'denied':
            return None, dict(dispositivo_id=device['id'], tipo='PERMISSAO_ICMP', mensagem='Operation not permitted')
        received = 0 if state['mode'] == 'down' else packets
        state['n'] += 1
        stamp = ec.utc_now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        return dict(id=f'00000000-0000-4000-8000-{state["n"]:012d}', dispositivo_id=device['id'], coletada_em=stamp,
                    enviados=packets, recebidos=received, latencia_ms=1.5 if received else None), None
    return fn


def count(app, model):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(model))


def test_outage_queue_retry_and_incident_cycle(app, server, remote, device, tmp_path):
    state = dict(mode='up', n=0)
    clock = Clock()
    queue = ec.Queue(tmp_path / 'fila.jsonl', 100)
    collector = ec.Collector(ec.Api(server, remote['token'], timeout=3), queue, 1, fake_measure(state), clock)
    collector.step()
    assert count(app, Metrica) == 1 and len(queue) == 0
    # API unreachable: measurements continue and wait on disk.
    collector.api.base = 'http://127.0.0.1:9'
    state['mode'] = 'down'
    for _ in range(3):
        clock.now += 31
        collector.step()
    assert len(queue) >= 1 and collector.backoff >= 2
    assert (tmp_path / 'fila.jsonl').read_text().count('\n') == len(queue)
    # Restart from disk (process restart) and reconnect.
    collector2 = ec.Collector(ec.Api(server, remote['token'], timeout=3), ec.Queue(tmp_path / 'fila.jsonl', 100), 1, fake_measure(state), clock)
    for _ in range(4):
        clock.now += 31
        collector2.step()
    assert len(collector2.queue) == 0
    with app.app_context():
        assert db.session.scalar(select(Dispositivo)).status == 'OFFLINE'
        assert db.session.scalar(select(func.count()).select_from(Falha)) == 1
    state['mode'] = 'up'
    for _ in range(2):
        clock.now += 31
        collector2.step()
    with app.app_context():
        assert db.session.scalar(select(Falha)).estado == 'ENCERRADA'
        assert db.session.scalar(select(func.count()).select_from(Falha)) == 1
    # Resending everything already confirmed creates nothing new.
    before = count(app, Metrica)
    collector2.queue.add([dict(id=f'00000000-0000-4000-8000-{1:012d}', dispositivo_id=device['id'],
                               coletada_em=ec.utc_now().isoformat().replace('+00:00', 'Z'), enviados=4, recebidos=4, latencia_ms=1.5)])
    collector2.flush()
    assert count(app, Metrica) == before and len(collector2.queue) == 0


def test_permission_error_and_revocation(app, server, remote, signed, tmp_path):
    state = dict(mode='denied', n=0)
    collector = ec.Collector(ec.Api(server, remote['token'], timeout=3), ec.Queue(tmp_path / 'q.jsonl', 100), 1, fake_measure(state), Clock())
    collector.step()
    listed = signed.get('/api/dispositivos').json[0]
    assert 'ICMP' in listed['erro_coleta'] and listed['status'] is None
    assert count(app, Metrica) == 0 and count(app, Falha) == 0
    signed.post(f'/api/coletores/{remote["coletor"]["id"]}/revogar', json={}, headers=auth_headers(signed))
    collector.config_at = None
    with pytest.raises(ec.AuthError):
        collector.step()


def test_bounded_queue_and_https_requirement(tmp_path):
    queue = ec.Queue(tmp_path / 'q.jsonl', 100)
    queue.add([dict(id=str(i)) for i in range(150)])
    assert len(queue) == 100 and queue.head(1)[0]['id'] == '50'
    with pytest.raises(SystemExit):
        ec.check_url('http://edgehealth.example.org', False)
    assert ec.check_url('http://127.0.0.1:5000', False)
    assert ec.check_url('https://edgehealth.example.org', False)


@pytest.mark.real_network
@pytest.mark.skipif(os.getenv('EDGEHEALTH_TEST_REAL_NETWORK') != '1', reason='Habilite teste ICMP de loopback explicitamente.')
def test_real_icmp_through_remote_collector(app, server, remote, signed, tmp_path):
    collector = ec.Collector(ec.Api(server, remote['token'], timeout=5), ec.Queue(tmp_path / 'r.jsonl', 100), 1)
    collector.step()
    with app.app_context():
        metric = db.session.scalar(select(Metrica))
        assert metric and metric.respondeu and metric.pacotes_recebidos == metric.pacotes_enviados
        assert metric.coletor_id == remote['coletor']['id'] and metric.latencia_ms is not None
    assert signed.get('/api/dispositivos').json[0]['status'] == 'ONLINE'
