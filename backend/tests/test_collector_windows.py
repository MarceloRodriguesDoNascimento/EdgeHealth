"""Windows wrapper of the collector: connection messages and scheduled-task definition.

The window, icacls and schtasks need a Windows desktop; they are exercised manually (see
collector/README.md). Everything decided in code is tested here, on any OS.
"""
import sys
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from werkzeug.serving import make_server
from conftest import auth_headers

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'collector' / 'windows'))
import edgehealth_windows as ew  # noqa: E402

NS = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


class FakeApi:
    def __init__(self, outcome):
        self.outcome = outcome

    def __call__(self, url, token, timeout):
        return self

    def call(self, method, path):
        assert (method, path) == ('GET', '/api/coletor/configuracao')
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def config(devices=2, server=NOW):
    return dict(servidor_em=server.isoformat().replace('+00:00', 'Z'), dispositivos=[dict(id=i) for i in range(devices)])


@pytest.mark.parametrize('outcome,expected', [
    (config(2), 'Conectado — 2 dispositivos'),
    (config(1), 'Conectado — 1 dispositivo'),
    (ew.core.AuthError('x'), 'Credencial inválida ou revogada'),
    (ew.core.ApiUnavailable('Sem conexão com a API: URLError'), 'Sem conexão com o servidor'),
    (ew.core.ApiUnavailable('API respondeu HTTP 503'), 'O servidor não aceitou a conexão agora'),
    (config(server=NOW - timedelta(minutes=5)), 'está 5 min adiantado'),
    (config(server=NOW + timedelta(minutes=3)), 'está 3 min atrasado'),
])
def test_connection_messages_for_people(outcome, expected):
    ok, message, _ = ew.test_connection('https://edgehealth.example', 'ehc_abc', FakeApi(outcome), now=lambda: NOW)
    assert expected in message
    assert ok == message.startswith('Conectado')


def test_connection_rejects_wrong_credential_format_and_plain_http_before_any_request():
    never = FakeApi(AssertionError('não deveria chamar a API'))
    assert 'começa com "ehc_"' in ew.test_connection('https://x.example', 'abc', never)[1]
    assert 'https://' in ew.test_connection('http://x.example', 'ehc_abc', never)[1]


def test_connection_against_the_real_collector_api(app, signed):
    created = signed.post('/api/coletores', json={'nome': 'Coletor Windows'}, headers=auth_headers(signed))
    token = created.json['token']
    srv = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f'http://127.0.0.1:{srv.server_port}'  # HTTP is accepted only for localhost
        assert ew.test_connection(url, token) == (True, 'Conectado — 0 dispositivos', 0)
        assert ew.test_connection(url, token[:-2] + 'xx')[0] is False
    finally:
        srv.shutdown()


@pytest.mark.parametrize('scope,trigger,user', [('maquina', 'BootTrigger', 'S-1-5-18'), ('usuario', 'LogonTrigger', 'S-1-5-21-1-2-3-1001')])
def test_task_is_hidden_unlimited_and_restarts_on_failure(scope, trigger, user):
    xml = ew.task_xml(scope, r'C:\ProgramData\EdgeHealth\EdgeHealthColetor.exe', r'--servico --dados "C:\Pasta & Cia"', user)
    root = ET.fromstring(xml.split('\n', 1)[1])  # the declaration says UTF-16 (file encoding for schtasks)
    assert root.find(f't:Triggers/t:{trigger}', NS) is not None
    assert root.findtext('t:Principals/t:Principal/t:UserId', namespaces=NS) == user
    settings = root.find('t:Settings', NS)
    assert settings.findtext('t:Hidden', namespaces=NS) == 'true'
    assert settings.findtext('t:ExecutionTimeLimit', namespaces=NS) == 'PT0S'
    assert settings.findtext('t:RestartOnFailure/t:Interval', namespaces=NS) == 'PT1M'
    assert settings.findtext('t:DisallowStartIfOnBatteries', namespaces=NS) == 'false'
    assert settings.findtext('t:MultipleInstancesPolicy', namespaces=NS) == 'IgnoreNew'
    assert root.findtext('t:Actions/t:Exec/t:Arguments', namespaces=NS) == r'--servico --dados "C:\Pasta & Cia"'


def test_bundled_certificates_are_installed_for_the_collector_requests():
    # certifi ships inside the .exe (build.ps1); the backend environment may not have it.
    pytest.importorskip('certifi')
    import urllib.request
    previous = urllib.request._opener
    try:
        context = ew.use_bundled_certificates()
        handler = next(h for h in urllib.request._opener.handlers if isinstance(h, urllib.request.HTTPSHandler))
        assert handler._context is context and context.verify_mode.name == 'CERT_REQUIRED'
    finally:
        urllib.request.install_opener(previous)


def test_restricted_machine_install_is_reported_not_crashing(monkeypatch, tmp_path):
    # Opened without elevation, the machine-wide folder (SYSTEM/Administrators only) is unreadable.
    class Locked(type(tmp_path)):
        def exists(self, *a, **k):
            raise PermissionError(13, 'Acesso negado')
    monkeypatch.setattr(ew, 'scope_dir', lambda scope: Locked(tmp_path / scope))
    assert ew.installed() == ('maquina', tmp_path / 'maquina')
