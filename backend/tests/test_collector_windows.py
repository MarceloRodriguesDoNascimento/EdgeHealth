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


# --- Regression: install made from a terminal inside an MSIX-packaged app (Claude desktop) -----
# Writes to %LOCALAPPDATA% were redirected to Packages/<family>/LocalCache/Local, the task kept
# the path the installer saw, and Task Scheduler (outside the package) failed with 0x80070002.

def test_long_path_prefixes_are_removed():
    assert ew.strip_long_prefix(r'\\?\C:\Users\a\AppData\Local\Packages\P\LocalCache\Local\EdgeHealth') == \
        r'C:\Users\a\AppData\Local\Packages\P\LocalCache\Local\EdgeHealth'
    assert ew.strip_long_prefix(r'\\?\UNC\srv\share\EdgeHealth') == r'\\srv\share\EdgeHealth'
    assert ew.strip_long_prefix(r'C:\plain') == r'C:\plain'


@pytest.mark.skipif(sys.platform != 'win32', reason='GetFinalPathNameByHandle')
def test_physical_path_of_a_normal_folder_is_itself(tmp_path):
    import os
    assert os.path.normcase(ew.physical(tmp_path)) == os.path.normcase(tmp_path.resolve())


@pytest.fixture
def fake_windows(monkeypatch, tmp_path):
    """Isolated LOCALAPPDATA/ProgramData and a recorder instead of schtasks/icacls/taskkill."""
    local, program_data = tmp_path / 'Local', tmp_path / 'ProgramData'
    local.mkdir(); program_data.mkdir()
    monkeypatch.setenv('LOCALAPPDATA', str(local)); monkeypatch.setenv('ProgramData', str(program_data))
    calls = []

    class Done:
        returncode, stdout, stderr = 0, '', ''

    def run(args, check=True):
        entry = list(args)
        if '/XML' in args and args[0] == 'schtasks' and '/Create' in args:
            entry.append(Path(args[args.index('/XML') + 1]).read_text(encoding='utf-16'))
        calls.append(entry)
        return Done()
    monkeypatch.setattr(ew, 'run', run)
    monkeypatch.setattr(ew, 'current_user_sid', lambda: 'S-1-5-21-1-2-3-1001')
    monkeypatch.setattr(ew, 'packaged', lambda: False)
    return local, calls


def virtual_install(local):
    d = local / 'Packages' / 'Claude_pzs8sxrjxfjjc' / 'LocalCache' / 'Local' / 'EdgeHealth'
    (d / 'logs').mkdir(parents=True)
    (d / 'config.json').write_text('{"api_url": "https://x.example", "escopo": "usuario"}', encoding='utf-8')
    (d / 'coletor.token').write_text('ehc_mesma-credencial', encoding='ascii')
    (d / 'fila.jsonl').write_text('{"id": "a"}\n', encoding='utf-8')
    (d / 'logs' / 'coletor.log').write_text('antigo\n', encoding='utf-8')
    (d / 'coletor.pid').write_text('999999', encoding='ascii')
    return d


def created_task_xml(calls):
    return next(c[-1] for c in calls if c[:2] == ['schtasks', '/Create'])


def test_install_redirected_by_a_package_is_found_from_outside(fake_windows):
    local, _ = fake_windows
    d = virtual_install(local)
    assert ew.installed() == ('usuario', d)


def test_task_points_to_the_physical_folder(fake_windows, monkeypatch, tmp_path):
    local, calls = fake_windows
    seen, real = local / 'EdgeHealth', virtual_install(local)
    monkeypatch.setattr(ew, 'physical', lambda p: real if Path(p) == seen else Path(p))
    ew.register_task('usuario', seen)
    xml = created_task_xml(calls)
    assert f'--dados "{real}"' in xml and f'--dados "{seen}"' not in xml


def test_repair_moves_a_redirected_install_keeping_credential_and_queue(fake_windows):
    local, calls = fake_windows
    source = virtual_install(local)
    target = ew.repair()
    assert target == local / 'EdgeHealth'
    assert (target / 'coletor.token').read_text(encoding='ascii') == 'ehc_mesma-credencial'
    assert (target / 'fila.jsonl').read_text(encoding='utf-8') == '{"id": "a"}\n'
    assert (target / 'logs' / 'coletor.log').exists() and not (target / 'coletor.pid').exists()
    assert not source.exists()
    assert ['taskkill', '/PID', '999999', '/T', '/F'] in calls  # the copy started by hand is ended
    assert f'--dados "{target}"' in created_task_xml(calls)
    assert ['schtasks', '/Run', '/TN', ew.TASK] in calls


def test_single_instance_lock_follows_the_physical_folder_not_the_task_name(monkeypatch, tmp_path):
    # The isolated test install collided with the real one because the lock used a fixed name.
    seen, real, other = tmp_path / 'seen', tmp_path / 'real', tmp_path / 'other'
    monkeypatch.setattr(ew, 'physical', lambda p: real if Path(p) in (seen, real) else Path(p))
    assert ew.instance_name('usuario', seen) == ew.instance_name('usuario', real)  # hand-started copy vs task
    assert ew.instance_name('usuario', other) != ew.instance_name('usuario', real)
    assert ew.instance_name('maquina', real).startswith('Global\\') and ew.instance_name('usuario', real).startswith('Local\\')
