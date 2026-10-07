"""EdgeHealth network lab orchestrator (Windows side).

Drives the WSL2 lab (lab.sh) and the hosted EdgeHealth API to reproduce every kind of
failure and diagnosis, checking each expected result through the API.

    python tests/lab/edgelab.py noturno         # everything, unattended (~1h40): see README
    python tests/lab/edgelab.py preparar        # account, collector and devices (idempotent)
    python tests/lab/edgelab.py subir           # lab + collector running in the background
    python tests/lab/edgelab.py status          # lab and EdgeHealth view side by side
    python tests/lab/edgelab.py falha offline impressora   # manual fault injection
    python tests/lab/edgelab.py cenario [--prints] [--so 2,3]
    python tests/lab/edgelab.py descer          # stop collector and remove the lab

Credentials live in tests/lab/.credenciais-lab.json and tests/lab/.coletor-lab.token
(git-ignored, owner-only ACL). They are never printed or logged.
Standard library only.
"""
import argparse
import ctypes
import http.cookiejar
import io
import json
import os
import secrets
import ssl
import string
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
CREDS = LAB / '.credenciais-lab.json'
TOKEN = LAB / '.coletor-lab.token'
LOG = LAB / 'execucao.log'
REPORT = LAB / 'relatorio.md'
EVIDENCE = LAB / 'evidencias'
API = os.getenv('EDGEHEALTH_API_URL', 'https://marcelodomingos.pythonanywhere.com')
DISTRO = os.getenv('EDGEHEALTH_WSL_DISTRO', 'Ubuntu-24.04')
INTERVAL = int(os.getenv('EDGEHEALTH_INTERVALO', '60'))  # MONITOR_INTERVAL in production
WINDOW = 300             # DIAGNOSTIC_WINDOW_SECONDS
COLLECTOR_STALE = 240    # COLLECTOR_STALE_SECONDS in production (.env of PythonAnywhere)
CRITICAL_MINUTES = 60    # SEVERITY_CRITICAL_MINUTES (backend/app/config.py)
COMPANY = 'Empresa TESTE LAB'
COMPANY_B = 'Empresa TESTE LAB B'
COLLECTOR = 'Coletor TESTE LAB'

# key -> (name, type, location, ip). Lab keys match lab.sh; the last two are real targets.
DEVICES = {
    'firewall':   ('Firewall', 'Firewall', 'Datacenter', '10.77.0.2'),
    'servidor':   ('Servidor de arquivos', 'Servidor', 'Datacenter', '10.77.0.3'),
    'nas':        ('NAS', 'Armazenamento (NAS)', 'Datacenter', '10.77.0.4'),
    'impressora': ('Impressora', 'Impressora', 'Térreo - recepção', '10.77.0.5'),
    'desktop':    ('Desktop', 'Desktop', 'Térreo - financeiro', '10.77.0.6'),
    'sensor':     ('Sensor IoT', 'Sensor IoT', 'Almoxarifado', '10.77.0.7'),
    'switch2':    ('Switch andar 2', 'Switch', 'Andar 2 - rack', '10.77.2.2'),
    'ap':         ('Access Point', 'Access Point', 'Andar 2 - corredor', '10.77.2.3'),
    'camera':     ('Câmera IP', 'Câmera IP', 'Andar 2 - entrada', '10.77.2.4'),
    'voip':       ('Telefone VoIP', 'Telefone VoIP', 'Andar 2 - sala de reunião', '10.77.2.5'),
    'cloudflare': ('DNS Cloudflare', 'Serviço externo', 'Internet', '1.1.1.1'),
    'testnet':    ('Host inexistente (TEST-NET)', 'Serviço externo', 'Internet', '192.0.2.1'),
}
ANDAR2 = ['switch2', 'ap', 'camera', 'voip']


def now():
    return datetime.now(timezone.utc)


# Offset between the EdgeHealth server and this Windows clock, from the HTTP "Date" header.
# Failure times come from the server/collector clock; this Windows clock may be minutes off,
# so every "since" and time window must use server_now(), never now().
CLOCK = {'offset': timedelta(0)}


def server_now():
    return now() + CLOCK['offset']


def track_server_clock(headers):
    try:
        server = parsedate_to_datetime(headers['Date'])
        local = now()
        offset = server - local
        # The Date header has 1 s resolution: ignore sub-second jitter.
        if abs((offset - CLOCK['offset']).total_seconds()) > 1:
            CLOCK['offset'] = offset
    except (KeyError, TypeError, ValueError):
        pass


def say(msg):
    line = f'[{now().astimezone():%H:%M:%S}] {msg}'
    print(line, flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def keep_awake(on=True):
    """Prevents idle sleep while this process runs (no system setting is changed)."""
    if os.name == 'nt':
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


# --- WSL --------------------------------------------------------------------------------
def wsl_path(p):
    p = Path(p).resolve()
    return '/mnt/' + p.drive[0].lower() + p.as_posix()[2:]


def wsl_cmd(*args):
    return ['wsl.exe', '-d', DISTRO, '-u', 'root', '--cd', wsl_path(ROOT), '--', 'bash', 'tests/lab/lab.sh', *args]


def lab(*args, check=True):
    out = subprocess.run(wsl_cmd(*args), capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and out.returncode:
        raise RuntimeError(f'lab.sh {" ".join(args)} falhou: {out.stderr.strip() or out.stdout.strip()}')
    return out.stdout


def spawn_hidden(*args):
    """Long-lived wsl.exe: keeps the WSL VM (and the lab) alive after the caller exits."""
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        subprocess.Popen(wsl_cmd(*args), creationflags=flags | 0x01000000, **kw)  # + BREAKAWAY_FROM_JOB
    except OSError:
        subprocess.Popen(wsl_cmd(*args), creationflags=flags, **kw)


def collector_running():
    return 'Coletor: rodando' in lab('status', check=False)


def start_collector():
    if collector_running():
        return
    spawn_hidden('coletor', API, wsl_path(TOKEN))
    for _ in range(60):
        time.sleep(2)
        if collector_running():
            say('Coletor do lab rodando no WSL.')
            return
    raise RuntimeError('O coletor não iniciou. Veja: python tests/lab/edgelab.py log')


def ensure_lab():
    """Keepalive + namespaces + clock. Safe to repeat (the VM may have been restarted)."""
    if 'lab não está de pé' in lab('status', check=False) or 'DISPOSITIVO' not in lab('status', check=False):
        say('Lab não estava de pé: subindo de novo.')
        spawn_hidden('manter'); time.sleep(3)
        lab('up')
    lab('hora', API, check=False)


# --- API --------------------------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f'HTTP {status}: {body.get("erro") if isinstance(body, dict) else body}')
        self.status, self.body = status, body


def tls_context():
    """This Windows certificate store fails on the Let's Encrypt chain ("certificate has expired")
    while curl and WSL accept it; Git's CA bundle is used when present. Verification stays on."""
    bundle = Path(os.getenv('EDGEHEALTH_CA_BUNDLE', r'C:\Program Files\Git\mingw64\etc\ssl\certs\ca-bundle.crt'))
    return ssl.create_default_context(cafile=str(bundle)) if bundle.exists() else ssl.create_default_context()


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                                  urllib.request.HTTPSHandler(context=tls_context()))

    def csrf(self):
        return next((c.value for c in self.jar if c.name == 'edgehealth_csrf'), '')

    def call(self, method, path, body=None, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(API + '/api' + path, data=data, method=method,
                                     headers={'Content-Type': 'application/json', 'X-CSRF-Token': self.csrf(),
                                              'User-Agent': 'edgehealth-lab/1.0'})
        for attempt in range(5):
            try:
                with self.opener.open(req, timeout=30) as r:
                    track_server_clock(r.headers)
                    payload = r.read()
                    return payload if raw else json.loads(payload or b'null')
            except urllib.error.HTTPError as e:
                track_server_clock(e.headers)
                text = e.read().decode(errors='replace')
                try:
                    parsed = json.loads(text)
                except ValueError:
                    parsed = text[:200]
                if (e.code >= 500 or e.code == 429) and attempt < 4:
                    time.sleep(10); continue
                raise ApiError(e.code, parsed) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 4:
                    raise
                time.sleep(10)

    def status_of(self, method, path, body=None):
        try:
            self.call(method, path, body)
            return 200
        except ApiError as e:
            return e.status

    def get(self, path): return self.call('GET', path)
    def post(self, path, body=None): return self.call('POST', path, body if body is not None else {})
    def put(self, path, body): return self.call('PUT', path, body)
    def delete(self, path): return self.call('DELETE', path)


def load_creds():
    if not CREDS.exists():
        raise SystemExit('Rode primeiro: python tests/lab/edgelab.py preparar')
    return json.loads(CREDS.read_text(encoding='utf-8'))


def write_secret(path, text):
    path.write_text(text, encoding='ascii', newline='')
    subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', f'{os.environ["USERNAME"]}:(R,W)'],
                   capture_output=True, check=True)


def random_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(24))


def test_cnpj():
    """Random CNPJ with valid check digits (same algorithm as backend/app/validation.py)."""
    base = [secrets.randbelow(10) for _ in range(8)] + [0, 0, 0, 1]
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        rem = sum(d * w for d, w in zip(base, weights)) % 11
        base.append(0 if rem < 2 else 11 - rem)
    return ''.join(map(str, base))


def login(account='admin'):
    creds = load_creds()[account]
    c = Client()
    c.post('/auth/login', dict(email=creds['email'], senha=creds['senha']))
    return c


def devices_by_key(c):
    by_ip = {d['ip']: d for d in c.get('/dispositivos?arquivados=1')}
    return {k: by_ip.get(v[3]) for k, v in DEVICES.items()}


# --- Setup commands -----------------------------------------------------------------------
def preparar(_=None):
    if CREDS.exists():
        c = login()
        say('Conta de teste já existe; login ok.')
    else:
        creds = dict(admin=dict(email=f'lab-{secrets.token_hex(4)}@example.com', senha=random_password()))
        c = Client()
        c.post('/auth/registro', dict(nome_fantasia=COMPANY, cnpj=test_cnpj(), nome='Admin TESTE LAB',
                                      email=creds['admin']['email'], senha=creds['admin']['senha'], aceite_termos=True))
        write_secret(CREDS, json.dumps(creds, indent=2))
        say(f'"{COMPANY}" criada e Termos aceitos (credenciais em {CREDS.name}).')
    collectors = [x for x in c.get('/coletores') if x['nome'] == COLLECTOR and not x['revogado_em']]
    if collectors and TOKEN.exists():
        collector = collectors[0]
    elif collectors:
        r = c.post(f'/coletores/{collectors[0]["id"]}/rotacionar')
        collector = r['coletor']; write_secret(TOKEN, r['token'])
        say('Credencial do coletor rotacionada (token local ausente).')
    else:
        r = c.post('/coletores', dict(nome=COLLECTOR))
        collector = r['coletor']; write_secret(TOKEN, r['token'])
        say(f'"{COLLECTOR}" cadastrado (token em {TOKEN.name}).')
    existing = devices_by_key(c)
    for key, (name, kind, place, ip) in DEVICES.items():
        d = existing[key]
        if d is None:
            c.post('/dispositivos', dict(nome=name, ip=ip, tipo=kind, localizacao=place, coletor_id=collector['id']))
            say(f'Dispositivo criado: {name} ({ip})')
        elif d['arquivado_em']:
            c.post(f'/dispositivos/{d["id"]}/desarquivar')
            say(f'Dispositivo desarquivado: {name}')
        elif d['coletor_id'] != collector['id']:
            c.put(f'/dispositivos/{d["id"]}', dict(coletor_id=collector['id']))
    say(f'Pronto: {len(DEVICES)} dispositivos atribuídos ao {COLLECTOR}.')


def subir(_=None):
    load_creds()
    if not TOKEN.exists():
        raise SystemExit('Token do coletor ausente: rode preparar.')
    say('Subindo o lab no WSL...')
    spawn_hidden('manter')
    time.sleep(3)
    print(lab('up'))
    print(lab('hora', API).strip())
    start_collector()


def descer(_=None):
    print(lab('down', check=False))
    print(lab('liberar', check=False))


def status(_=None):
    print(lab('status', check=False))
    c = login()
    print(f'{"DISPOSITIVO":<30} {"IP":<11} {"STATUS":<9} {"LAT ms":>7} {"PERDA":>6}  ÚLTIMA COLETA')
    for key, d in devices_by_key(c).items():
        if not d:
            print(f'{DEVICES[key][0]:<30} (não cadastrado)'); continue
        lat = '-' if d['latencia_ms'] is None else f'{d["latencia_ms"]:.0f}'
        loss = '-' if d['perda_pacotes_pct'] is None else f'{d["perda_pacotes_pct"]:.0f}%'
        arch = ' ARQUIVADO' if d['arquivado_em'] else ''
        print(f'{d["nome"]:<30} {d["ip"]:<11} {(d["status"] or "-"):<9} {lat:>7} {loss:>6}  {d["ultima_coleta"] or "-"}{arch}')
    for col in c.get('/coletores'):
        print(f'Coletor "{col["nome"]}": {col["estado"]} (último contato {col["ultimo_contato"]})')
    opened = c.get('/falhas?estado=ABERTA&limite=50')['items']
    print(f'Falhas abertas: {len(opened)}' + ''.join(f'\n  - {f["dispositivo"]}: {f["tipo"]} {f["severidade"]}' for f in opened))


def falha(args):
    mapping = {'offline': ['offline'], 'latencia': ['latencia'], 'perda': ['perda'], 'degradar': ['degradar'],
               'restaurar': ['restaurar'], 'switch': ['switch-andar2'], 'coletor-parar': ['coletor-parar']}
    if args.acao == 'coletor-iniciar':
        start_collector(); return
    if args.acao not in mapping:
        raise SystemExit(f'Ação inválida. Use: {", ".join([*mapping, "coletor-iniciar"])}')
    print(lab(*mapping[args.acao], *args.args).strip())


def log(_=None):
    print(lab('log', '40', check=False))


# --- Scenario -------------------------------------------------------------------------------
class Scenario:
    def __init__(self, prints=False, night=False):
        self.c = login()
        self.prints, self.night = prints, night
        self.rows, self.morning = [], []
        self.last_offline = None
        self.testnet_failure = None
        self.run_dir = EVIDENCE / now().astimezone().strftime('%Y%m%d-%H%M')
        self.snap_no = 0
        self.ids = {k: d['id'] for k, d in devices_by_key(self.c).items() if d}
        missing = [k for k in DEVICES if k not in self.ids]
        if missing:
            raise SystemExit(f'Dispositivos ausentes: {missing}. Rode preparar.')

    # --- helpers
    def record(self, scenario, expected, obtained, ok, evidence=''):
        self.rows.append(dict(cenario=scenario, esperado=expected, obtido=obtained, ok=ok, evidencia=evidence))
        mark = 'OK   ' if ok else ('n/a  ' if ok is None else 'FALHA')
        say(f'{mark} [{scenario}] {expected} -> {obtained}')

    def step(self, name, fn, collector=True):
        """Runs one scenario; any error becomes a FALHA row and the run continues."""
        say(f'===== {name} =====')
        try:
            if collector:
                self.c = login()   # fresh session: an 8 h session never expires mid-run
                ensure_lab()
                if not collector_running():
                    say('Coletor não estava rodando: religando.')
                    start_collector()
            fn()
        except Exception as e:  # noqa: BLE001 - unattended run must go on
            self.record(name, 'executar sem erro', f'{type(e).__name__}: {str(e)[:200]}', False)
            with LOG.open('a', encoding='utf-8') as f:
                f.write(traceback.format_exc())
            try:
                lab('restaurar', 'todos', check=False)
            except Exception:  # noqa: BLE001
                pass

    def device(self, key):
        return self.c.get(f'/dispositivos/{self.ids[key]}')

    def failures(self, key, limit=10):
        return self.c.get(f'/falhas?dispositivo_id={self.ids[key]}&limite={limit}')['items']

    def latest_failure(self, key, since=None):
        return next((f for f in self.failures(key) if since is None or f['inicio'] >= since), None)

    def detail(self, failure):
        return self.c.get(f'/falhas/{failure["id"]}')

    def rules(self, failure):
        diag = self.detail(failure).get('diagnostico') or {}
        return [x['regra'] for x in diag.get('causas') or []], diag

    def wait(self, what, predicate, timeout):
        deadline = time.monotonic() + timeout
        while True:
            try:
                value = predicate()
            except ApiError as e:
                say(f'aviso ao consultar ({what}): {e}')
                value = None
            if value:
                return value
            if time.monotonic() > deadline:
                say(f'tempo esgotado esperando: {what}')
                return None
            time.sleep(15)

    def iso(self):
        # Failure "inicio" is the first sample after the injection, stamped by the collector
        # (synced to the server). Server time minus 5 s covers the Date header resolution.
        self.c.get('/termos')  # refreshes the server clock offset
        return (server_now() - timedelta(seconds=5)).isoformat(timespec='seconds').replace('+00:00', '')

    def snapshot(self, moment, failure_ids=()):
        """Night mode evidence: API JSON at a key moment (no credentials in any of these payloads)."""
        self.snap_no += 1
        self.run_dir.mkdir(parents=True, exist_ok=True)
        data = dict(momento=moment, capturado_em_servidor=server_now().isoformat())
        for name, path in [('dashboard', '/dashboard'), ('dispositivos', '/dispositivos?arquivados=1'),
                           ('falhas', '/falhas?limite=200'), ('coletores', '/coletores')]:
            try:
                data[name] = self.c.get(path)
            except Exception as e:  # noqa: BLE001
                data[name] = f'erro: {e}'
        for col in data.get('coletores') or []:
            if isinstance(col, dict):
                col.pop('token_prefixo', None)
        # Details (diagnosis, causes, evidence, recommendations) of the requested failures,
        # every open failure and every failure started in the last 15 minutes (server time).
        recent = (server_now() - timedelta(minutes=15)).isoformat(timespec='seconds').replace('+00:00', '')
        listed = data['falhas'].get('items', []) if isinstance(data['falhas'], dict) else []
        ids = list(dict.fromkeys([*failure_ids, *(f['id'] for f in listed if f['estado'] == 'ABERTA' or f['inicio'] >= recent)]))
        data['detalhes'] = {}
        for fid in ids[:30]:
            try:
                data['detalhes'][fid] = self.c.get(f'/falhas/{fid}')
            except Exception as e:  # noqa: BLE001
                data['detalhes'][fid] = f'erro: {e}'
        path = self.run_dir / f'{self.snap_no:02d}-{moment}.json'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return path.relative_to(LAB).as_posix()

    def moment(self, number, screen, filename, failure_ids=()):
        evidence = self.snapshot(filename.rsplit('.', 1)[0], failure_ids)
        if self.prints and not self.night:
            print(f'\n>>> PRINT {number}: abra "{screen}", capture com Win+Shift+S e salve em '
                  f'tests/lab/screenshots/{filename}. Depois tecle Enter.', flush=True)
            input()
        else:
            ids = ', '.join(f'#{i}' for i in failure_ids)
            self.morning.append(f'{number}. **{screen}**{" (falha " + ids + ")" if ids else ""} → `screenshots/{filename}` · evidência `{evidence}`')
        return evidence

    def spacing(self):
        """Unavailability scenarios start > DIAGNOSTIC_WINDOW apart, or they would correlate."""
        if self.last_offline:
            remaining = WINDOW + 30 - (time.monotonic() - self.last_offline)
            if remaining > 0:
                say(f'Aguardando {remaining:.0f} s para isolar o cenário da janela de correlação...')
                time.sleep(remaining)
        self.last_offline = time.monotonic()

    def closed(self, key, failure_id):
        f = next((x for x in self.failures(key, 50) if x['id'] == failure_id), None)
        return f if f and f['estado'] == 'ENCERRADA' else None

    def recover(self, keys, opened):
        lab('restaurar', *keys)
        for key in keys:
            f = opened.get(key)
            if not f:
                continue
            done = self.wait(f'recuperação de {key}', lambda: self.closed(key, f['id']), INTERVAL * 5)
            self.record('8 Recuperação', f'{DEVICES[key][0]}: encerrada por RECUPERACAO, diagnóstico preservado',
                        f'{done["encerramento"]}, {done["duracao_segundos"]:.0f} s, {done["severidade"]}' if done else 'continua aberta',
                        bool(done and done['encerramento'] == 'RECUPERACAO' and self.detail(done).get('diagnostico')),
                        f'falha #{f["id"]}')

    # --- scenarios
    def s0_baseline(self):
        healthy = [k for k in DEVICES if k != 'testnet']
        ok = self.wait('linha de base', lambda: all(self.device(k)['status'] == 'ONLINE' for k in healthy), INTERVAL * 6)
        bad = {k: s for k in healthy if (s := self.device(k)['status']) != 'ONLINE'}
        self.record('1 Saudável', '11 dispositivos ONLINE', 'todos ONLINE' if ok else f'fora: {bad}', bool(ok))
        d = self.wait('TEST-NET OFFLINE', lambda: (lambda x: x if x['status'] == 'OFFLINE' else None)(self.device('testnet')), INTERVAL * 5)
        f = self.latest_failure('testnet')
        self.record('9 OFFLINE permanente', '192.0.2.1 OFFLINE com INDISPONIBILIDADE aberta',
                    f'{d and d["status"]}, {f and f["tipo"]} {f and f["estado"]}',
                    bool(d and f and f['tipo'] == 'INDISPONIBILIDADE' and f['estado'] == 'ABERTA'), f'falha #{f and f["id"]}')
        self.testnet_failure = f
        self.last_offline = time.monotonic()
        self.snapshot('00-linha-de-base')

    def s2_localizada(self):
        self.spacing(); since = self.iso()
        lab('offline', 'impressora')
        self.wait('Impressora OFFLINE', lambda: self.device('impressora')['status'] == 'OFFLINE', INTERVAL * 5)
        f = self.latest_failure('impressora', since)
        rules, diag = self.rules(f) if f else ([], {})
        codes = [r['codigo'] for r in diag.get('recomendacoes') or []]
        self.record('2 Localizada', 'INDISPONIBILIDADE + LOCALIZADA, recomendações local-cabo/local-config',
                    f'{f and f["tipo"]}, regras={rules}, recs={codes}',
                    bool(f and f['tipo'] == 'INDISPONIBILIDADE' and 'LOCALIZADA' in rules and {'local-cabo', 'local-config'} <= set(codes)),
                    self.snapshot('impressora-localizada', [f['id']] if f else []))
        self.recover(['impressora'], {'impressora': f})

    def s3_compartilhada(self):
        self.spacing(); since = self.iso()
        lab('switch-andar2', 'down')
        self.wait('andar 2 OFFLINE', lambda: all(self.device(k)['status'] == 'OFFLINE' for k in ANDAR2), INTERVAL * 6)
        opened = {k: self.latest_failure(k, since) for k in ANDAR2}
        f = opened['switch2']
        rules, _ = self.rules(f) if f else ([], {})
        ids = [x['id'] for x in opened.values() if x]
        self.record('3 Compartilhada', '4 falhas abertas; Switch com COMPARTILHADA (+LOCALIZADA)',
                    f'{len(ids)} falhas, regras={rules}', bool(len(ids) == 4 and 'COMPARTILHADA' in rules),
                    f'falha #{f and f["id"]}')
        sev = self.detail(f)['severidade'] if f else None
        self.record('10 Severidade ALTA', 'Switch andar 2 ALTA (4 dispositivos relacionados >= 3)', sev, sev == 'ALTA')
        self.moment(1, 'Visão da rede com o andar 2 fora', '01-dashboard-andar2.png')
        self.moment(2, 'Histórico de falhas com as 4 falhas abertas', '02-historico-andar2.png', ids)
        self.moment(3, 'Detalhe da falha do Switch andar 2 (COMPARTILHADA)', '03-diagnostico-compartilhada.png', ids[:1])
        if f:
            r = self.c.put(f'/falhas/{f["id"]}/impacto', dict(usuarios_afetados=60, observacao='Teste do laboratório: andar 2 inteiro'))
            self.record('10 Severidade CRITICA (impacto)', '60 usuários afetados -> CRITICA', r['severidade'],
                        r['severidade'] == 'CRITICA', f'falha #{f["id"]}')
        lab('switch-andar2', 'up')
        self.recover(ANDAR2, opened)

    def degraded(self, scenario, key, netem, expected_rule, expected_state=None):
        since = self.iso()
        lab(*netem)
        f = self.wait(f'{key} INSTABILIDADE', lambda: self.latest_failure(key, since), INTERVAL * 4)
        seen, diag = set(), {}
        for _ in range(3):  # several analyses: random loss varies sample to sample
            if not f:
                break
            rules, diag = self.rules(f)
            seen.update(rules)
            if expected_rule in seen or (expected_state and diag.get('estado') == expected_state and not rules):
                break
            time.sleep(INTERVAL)
        if expected_state:
            ok = bool(f and diag.get('estado') == expected_state and not seen)
            obtained = f'{f and f["tipo"]}, estado={diag.get("estado")}, regras vistas={sorted(seen)}'
        else:
            ok = bool(f and f['tipo'] == 'INSTABILIDADE' and expected_rule in seen)
            obtained = f'{f and f["tipo"]}, regras vistas={sorted(seen)}'
        self.record(scenario, f'INSTABILIDADE + {expected_state or expected_rule}', obtained, ok,
                    self.snapshot(key + '-' + (expected_state or expected_rule).lower(), [f['id']] if f else []))
        self.recover([key], {key: f})

    def s4(self): self.degraded('4 Congestionamento', 'nas', ['degradar', 'nas', '250', '50'], 'CONGESTIONAMENTO')
    def s5(self): self.degraded('5 Latência', 'firewall', ['latencia', 'firewall', '300'], 'LATENCIA')
    def s6(self): self.degraded('6 Evidência insuficiente', 'voip', ['perda', 'voip', '50'], None, 'EVIDENCIA_INSUFICIENTE')

    def s7_recorrente(self):
        for cycle in range(1, 4):
            since = self.iso()
            lab('offline', 'sensor')
            f = self.wait(f'sensor queda {cycle}', lambda: self.latest_failure('sensor', since), INTERVAL * 4)
            say(f'Sensor IoT: queda {cycle}/3 registrada como falha #{f and f["id"]}')
            if cycle == 3:
                rules = []
                for _ in range(3):
                    rules = self.rules(f)[0] if f else []
                    if 'RECORRENTE' in rules:
                        break
                    time.sleep(INTERVAL)
                self.record('7 Recorrente', '3ª falha do Sensor com RECORRENTE', f'regras={rules}', 'RECORRENTE' in rules,
                            f'falha #{f and f["id"]}')
                self.moment(4, 'Detalhe da 3ª falha do Sensor IoT (RECORRENTE)', '04-diagnostico-recorrente.png', [f['id']] if f else [])
            lab('restaurar', 'sensor')
            # Each drop must be a separate incident: wait for the device itself to be ONLINE
            # (2 good samples), even when the failure was not found, before the next drop.
            back = self.wait(f'sensor volta {cycle}', lambda: self.device('sensor')['status'] == 'ONLINE'
                             and (not f or self.closed('sensor', f['id'])), INTERVAL * 6)
            if not back:
                raise RuntimeError(f'Sensor não voltou a ONLINE após a queda {cycle}: as quedas se fundiriam em uma falha só.')

    def s11_coletor(self):
        before = len(self.c.get('/falhas?estado=ABERTA&limite=50')['items'])
        lab('coletor-parar')
        say(f'Coletor parado; aguardando {COLLECTOR_STALE + 45} s...')
        time.sleep(COLLECTOR_STALE + 45)
        self.c = login()
        state = next(x['estado'] for x in self.c.get('/coletores') if x['nome'] == COLLECTOR)
        stale = sum(d['desatualizado'] for d in self.c.get('/dispositivos'))
        after = len(self.c.get('/falhas?estado=ABERTA&limite=50')['items'])
        self.record('11 Coletor parado', 'coletor DESATUALIZADO, dispositivos desatualizados, nenhuma falha nova',
                    f'{state}, {stale} desatualizados, falhas abertas {before}->{after}',
                    state == 'DESATUALIZADO' and stale > 0 and after <= before)
        self.moment(5, 'Visão da rede com o coletor sem contato', '05-coletor-parado.png')
        start_collector()
        ok = self.wait('coletor ATIVO', lambda: next(x['estado'] for x in self.c.get('/coletores') if x['nome'] == COLLECTOR) == 'ATIVO', INTERVAL * 3)
        self.record('11 Coletor religado', 'coletor volta a ATIVO', 'ATIVO' if ok else 'não voltou', bool(ok))
        self.wait('dispositivos atualizados', lambda: not any(d['desatualizado'] for d in self.c.get('/dispositivos')), INTERVAL * 4)

    def s12_arquivar(self):
        self.spacing(); since = self.iso()
        lab('offline', 'impressora')
        f = self.wait('falha da Impressora', lambda: self.latest_failure('impressora', since), INTERVAL * 4)
        did = self.ids['impressora']
        self.c.delete(f'/dispositivos/{did}')
        closed = next((x for x in self.failures('impressora', 50) if f and x['id'] == f['id']), None)
        active = [d['id'] for d in self.c.get('/dispositivos')]
        self.record('12 Arquivar', 'falha encerrada por ARQUIVAMENTO e dispositivo fora da lista ativa',
                    f'{closed and closed["encerramento"]}, na lista ativa={did in active}',
                    bool(closed and closed['encerramento'] == 'ARQUIVAMENTO' and did not in active), f'falha #{f and f["id"]}')
        lab('restaurar', 'impressora')
        restored = self.c.post(f'/dispositivos/{did}/desarquivar')
        back = self.wait('Impressora monitorada de novo',
                         lambda: (lambda d: d if d['status'] == 'ONLINE' and d['ultima_coleta'] else None)(self.device('impressora')),
                         INTERVAL * 5)
        history = [x['id'] for x in self.failures('impressora', 50)]
        self.record('12 Desarquivar', 'volta ONLINE com histórico preservado',
                    f'status={back and back["status"]}, falhas no histórico={len(history)}',
                    bool(restored['arquivado_em'] is None and back and f and f['id'] in history))

    # --- extra coverage
    def e_coleta_manual(self):
        before = self.device('servidor')['ultima_coleta']
        r = self.c.post(f'/dispositivos/{self.ids["servidor"]}/coletas')
        newer = self.wait('coleta manual', lambda: (lambda d: d if d['ultima_coleta'] != before else None)(self.device('servidor')), 50)
        self.record('Extra: coleta manual', '202 e nova medição em menos de 1 intervalo',
                    f'{r.get("mensagem", "")[:40]}..., nova coleta={bool(newer)}', bool(newer))

    def e_isolamento(self):
        creds = load_creds()
        if 'empresa_b' not in creds:
            creds['empresa_b'] = dict(email=f'lab-b-{secrets.token_hex(4)}@example.com', senha=random_password())
            Client().post('/auth/registro', dict(nome_fantasia=COMPANY_B, cnpj=test_cnpj(), nome='Admin TESTE LAB B',
                                                 email=creds['empresa_b']['email'], senha=creds['empresa_b']['senha'], aceite_termos=True))
            write_secret(CREDS, json.dumps(creds, indent=2))
        b = login('empresa_b')
        did = self.ids['servidor']
        fid = self.testnet_failure['id'] if self.testnet_failure else 0
        checks = {
            'GET dispositivo da A': b.status_of('GET', f'/dispositivos/{did}'),
            'PUT dispositivo da A': b.status_of('PUT', f'/dispositivos/{did}', dict(nome='invasao')),
            'coleta no dispositivo da A': b.status_of('POST', f'/dispositivos/{did}/coletas', {}),
            'GET falha da A': b.status_of('GET', f'/falhas/{fid}'),
            'impacto na falha da A': b.status_of('PUT', f'/falhas/{fid}/impacto', dict(usuarios_afetados=1)),
        }
        lists = (len(b.get('/dispositivos?arquivados=1')), b.get('/falhas')['total'], len(b.get('/coletores')))
        self.record('Extra: isolamento entre empresas', 'Empresa B recebe 404 e não vê nada da A',
                    f'{checks}, listas da B={lists}', all(s == 404 for s in checks.values()) and lists == (0, 0, 0))

    def e_tecnico(self):
        creds = load_creds()
        if 'tecnico' not in creds:
            creds['tecnico'] = dict(email=f'lab-tec-{secrets.token_hex(4)}@example.com', senha=random_password())
            self.c.post('/usuarios', dict(nome='Técnico TESTE LAB', email=creds['tecnico']['email'], senha=creds['tecnico']['senha']))
            write_secret(CREDS, json.dumps(creds, indent=2))
        t = login('tecnico')
        me = t.get('/auth/me')['usuario']
        pending = t.status_of('GET', '/dispositivos') if me['termos_pendentes'] else 'já aceitos'
        if me['termos_pendentes']:
            t.post('/auth/aceite-termos', dict(aceite_termos=True))
        checks = {
            'GET /usuarios': t.status_of('GET', '/usuarios'),
            'POST /usuarios': t.status_of('POST', '/usuarios', dict(nome='x', email='x@example.com', senha='senha-qualquer-1')),
            'POST /coletores': t.status_of('POST', '/coletores', dict(nome='x')),
            'PUT /empresa': t.status_of('PUT', '/empresa', dict(telefone='1')),
        }
        allowed = t.status_of('GET', '/dispositivos')
        self.record('Extra: técnico sem acesso de admin', 'TECNICO: 403 antes dos Termos e nas rotas de admin; lê dispositivos',
                    f'papel={me["papel"]}, antes dos Termos={pending}, admin={checks}, dispositivos={allowed}',
                    me['papel'] == 'TECNICO' and all(s == 403 for s in checks.values()) and allowed == 200
                    and pending in (403, 'já aceitos'))

    def e_filtros_detalhe(self):
        c = self.c
        sample = lambda q: c.get('/falhas?limite=200&' + q)['items']
        closed, high = sample('estado=ENCERRADA'), sample('severidade=ALTA')
        mine = sample(f'dispositivo_id={self.ids["sensor"]}')
        start = (server_now() - timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%S')
        period = sample(f'inicio={start}')
        bad = c.status_of('GET', '/falhas?estado=XYZ')
        ok = (closed and all(f['estado'] == 'ENCERRADA' for f in closed) and high and all(f['severidade'] == 'ALTA' for f in high)
              and mine and all(f['dispositivo_id'] == self.ids['sensor'] for f in mine) and period and bad == 400)
        self.record('Extra: filtros do histórico', 'estado, severidade, dispositivo e período filtram; valor inválido = 400',
                    f'encerradas={len(closed)}, altas={len(high)}, sensor={len(mine)}, período={len(period)}, inválido={bad}', bool(ok))
        # A failure whose diagnosis found causes (a long recovery-free incident may legitimately have none).
        f = next((d for d in (c.get(f'/falhas/{x["id"]}') for x in (high + closed)[:15])
                  if ((d.get('diagnostico') or {}).get('causas'))), None)
        diag = (f or {}).get('diagnostico') or {}
        d2 = c.get(f'/diagnosticos/{diag["id"]}') if diag.get('id') else {}
        ok = bool(f and diag.get('causas') and diag.get('recomendacoes') and f.get('justificativa', {}).get('motivos') and d2.get('falha_id') == f['id'])
        self.record('Extra: detalhe da falha', 'detalhe com diagnóstico, causas, recomendações e justificativa da severidade',
                    f'causas={len(diag.get("causas") or [])}, recs={len(diag.get("recomendacoes") or [])}, '
                    f'motivos={len((f or {}).get("justificativa", {}).get("motivos", []))}', ok, f'falha #{f and f["id"]}')

    def e_exportacao(self):
        data = self.c.call('GET', '/relatorios/exportar', raw=True)
        z = zipfile.ZipFile(io.BytesIO(data))
        csvs = sorted(n for n in z.namelist() if n.endswith('.csv'))
        content = {n: z.read(n).decode('utf-8-sig', errors='replace') for n in csvs}
        expected = ['diagnosticos.csv', 'dispositivos.csv', 'falhas.csv', 'metricas.csv']
        checks = dict(devices='Switch andar 2' in content.get('dispositivos.csv', ''),
                      metrics=content.get('metricas.csv', '').count('\n') > 50,
                      failures='INDISPONIBILIDADE' in content.get('falhas.csv', '') and 'INSTABILIDADE' in content.get('falhas.csv', ''),
                      diagnoses=all(r in content.get('diagnosticos.csv', '') for r in ('LOCALIZADA', 'COMPARTILHADA', 'LATENCIA')))
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / 'exportacao.zip').write_bytes(data)
        self.record('Extra: exportação ZIP', '4 CSVs com dispositivos, métricas, falhas e diagnósticos do lab',
                    f'CSVs={csvs}, conteúdo={checks}', csvs == expected and all(checks.values()),
                    (self.run_dir / 'exportacao.zip').relative_to(LAB).as_posix())

    def s10_severidade(self):
        t = self.testnet_failure
        if t and getattr(self, 'skip_critical_wait', False):
            f = self.c.get(f'/falhas/{t["id"]}')
            minutes = f['duracao_segundos'] / 60
            self.record('10 Severidade CRITICA (duração)', f'192.0.2.1 aberta há {CRITICAL_MINUTES}+ min -> CRITICA',
                        f'{f["severidade"]} com {minutes:.0f} min (espera desligada)',
                        f['severidade'] == 'CRITICA' if minutes >= CRITICAL_MINUTES else None, f'falha #{t["id"]}')
        elif t:
            elapsed = lambda: self.c.get(f'/falhas/{t["id"]}')['duracao_segundos'] / 60
            if elapsed() < CRITICAL_MINUTES + 1:
                wait = (CRITICAL_MINUTES + 1 - elapsed()) * 60
                say(f'Aguardando {wait / 60:.0f} min até o TEST-NET completar {CRITICAL_MINUTES} min fora do ar...')
                while wait > 0:  # short sleeps keep the collector watchdog running
                    time.sleep(min(wait, 300)); wait -= 300
                    if not collector_running():
                        start_collector()
            self.c = login()
            f = self.c.get(f'/falhas/{t["id"]}')
            self.record('10 Severidade CRITICA (duração)', f'192.0.2.1 aberta há {CRITICAL_MINUTES}+ min -> CRITICA',
                        f'{f["severidade"]} com {f["duracao_segundos"] / 60:.0f} min, motivos={f["justificativa"]["motivos"]}',
                        f['severidade'] == 'CRITICA' and f['estado'] == 'ABERTA', f'falha #{t["id"]}')
        levels = {}
        for f in self.c.get('/falhas?limite=200')['items']:
            levels.setdefault(f['severidade'], set()).add(f['dispositivo'])
        self.record('10 Severidades', 'BAIXA, MEDIA, ALTA e CRITICA presentes',
                    '; '.join(f'{k}: {", ".join(sorted(v))}' for k, v in sorted(levels.items())),
                    {'BAIXA', 'MEDIA', 'ALTA', 'CRITICA'} <= set(levels), self.snapshot('severidades'))

    def report(self, started, path=REPORT):
        failed = [r for r in self.rows if r['ok'] is False]
        lines = ['# Relatório do laboratório EdgeHealth', '',
                 f'- Produção: {API}', f'- Execução: {started.astimezone():%d/%m/%Y %H:%M} → {now().astimezone():%H:%M}',
                 f'- Resultado: **{len(self.rows) - len(failed)}/{len(self.rows)} OK**', f'- Log: `execucao.log` · evidências: `{self.run_dir.relative_to(LAB).as_posix()}/`', '',
                 '| Cenário | Esperado | Obtido | Resultado | Evidência |', '|---|---|---|---|---|']
        esc = lambda s: str(s).replace('|', '\\|').replace('\n', ' ')
        for r in self.rows:
            result = 'OK' if r['ok'] else ('n/a' if r['ok'] is None else '**FALHA**')
            lines.append(f'| {esc(r["cenario"])} | {esc(r["esperado"])} | {esc(r["obtido"])} | {result} | {esc(r["evidencia"])} |')
        if self.morning:
            lines += ['', '## Prints para tirar de manhã', '',
                      'Os momentos já passaram; o estado ficou registrado nas evidências JSON. Para a apresentação, capture as telas '
                      'equivalentes pelo histórico (filtre pelo dispositivo e abra a falha indicada):', '', *self.morning,
                      f'{len(self.morning) + 1}. **Histórico de falhas com tudo encerrado** → `screenshots/06-historico-final.png`']
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        say(f'Relatório: tests/lab/{path.name} — {len(self.rows) - len(failed)}/{len(self.rows)} OK')


def cenario(args):
    # --so takes scenario numbers and extra names: 2,3,4,5,6,7,11,12,manual,tecnico,isolamento,detalhe,exportacao
    only = {x.strip() for x in args.so.split(',')} if args.so else None
    run = lambda key: only is None or str(key) in only
    (LAB / 'screenshots').mkdir(exist_ok=True)
    started = now()
    s = Scenario(args.prints, args.noturno)
    s.skip_critical_wait = args.sem_espera_critica
    keep_awake(True)
    try:
        ensure_lab()
        lab('restaurar', 'todos')
        start_collector()
        s.step('0 Linha de base (1 e 9)', s.s0_baseline)
        steps = [('manual', 'Extra: coleta manual', s.e_coleta_manual), ('tecnico', 'Extra: técnico', s.e_tecnico),
                 ('isolamento', 'Extra: isolamento', s.e_isolamento),
                 (2, '2 Localizada', s.s2_localizada), (3, '3 Compartilhada', s.s3_compartilhada),
                 (4, '4 Congestionamento', s.s4), (5, '5 Latência', s.s5), (6, '6 Evidência insuficiente', s.s6),
                 (7, '7 Recorrente', s.s7_recorrente), (11, '11 Coletor parado', s.s11_coletor),
                 (12, '12 Arquivar/desarquivar', s.s12_arquivar),
                 ('detalhe', 'Extra: filtros e detalhe', s.e_filtros_detalhe), ('exportacao', 'Extra: exportação', s.e_exportacao)]
        for key, name, fn in steps:
            if run(key):
                s.step(name, fn)
        s.step('10 Severidade', s.s10_severidade)
        s.moment(6, 'Histórico de falhas com tudo encerrado', '06-historico-final.png') if not args.noturno else s.snapshot('final')
    except KeyboardInterrupt:
        say('Interrompido pelo usuário.')
    finally:
        say('Final: restaurando o lab e parando o coletor.')
        for cmd in (['restaurar', 'todos'], ['coletor-parar']):
            try:
                print(lab(*cmd, check=False).strip())
            except Exception:  # noqa: BLE001
                pass
        if args.noturno:
            lab('liberar', check=False)
        keep_awake(False)
        # A partial re-run (--so) keeps the full night report intact.
        s.report(started, LAB / 'relatorio-reexecucao.md' if args.so else REPORT)


def noturno(_):
    LOG.write_text('', encoding='utf-8')
    say('Lab noturno iniciado. Duração prevista: ~1h40. Não feche esta janela.')
    keep_awake(True)
    preparar()
    subir()
    cenario(argparse.Namespace(so=None, prints=False, noturno=True, sem_espera_critica=False))


def main():
    p = argparse.ArgumentParser(description='Laboratório de rede do EdgeHealth')
    sub = p.add_subparsers(dest='cmd', required=True)
    for name, fn in [('noturno', noturno), ('preparar', preparar), ('subir', subir), ('descer', descer),
                     ('status', status), ('log', log)]:
        sub.add_parser(name).set_defaults(fn=fn)
    f = sub.add_parser('falha', help='offline D | latencia D MS | perda D PCT | degradar D MS PCT | '
                                     'restaurar [D|todos] | switch up|down | coletor-parar | coletor-iniciar')
    f.add_argument('acao'); f.add_argument('args', nargs='*'); f.set_defaults(fn=falha)
    c = sub.add_parser('cenario')
    c.add_argument('--prints', action='store_true', help='pausa nos 6 momentos de captura de tela')
    c.add_argument('--noturno', action='store_true', help='sem pausas; evidências JSON e lista de prints no relatório')
    c.add_argument('--so', help='só estes, ex.: 2,3,7,detalhe (a linha de base e a severidade sempre rodam)')
    c.add_argument('--sem-espera-critica', action='store_true', help='não espera 60 min pelo TEST-NET')
    c.set_defaults(fn=cenario)
    args = p.parse_args()
    try:
        args.fn(args)
    except ApiError as e:
        raise SystemExit(f'API recusou: {e}')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
