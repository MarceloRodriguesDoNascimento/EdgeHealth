"""EdgeHealth remote collector.

Runs inside the company network, measures the devices assigned to it by the hosted
EdgeHealth API (ICMP: packets sent/received and latency) and sends the raw samples
over HTTPS. It never decides status, incidents, severity or diagnosis: the server does.

Only outbound HTTPS is used; no inbound port is opened in the company network.
Standard library + icmplib only.
"""
import argparse
import json
import logging
import os
import random
import signal
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from icmplib import ping
from icmplib.exceptions import ICMPLibError, SocketPermissionError

VERSION = '1.0.0'
FINAL = {'ACEITA', 'DUPLICADA', 'ATRASADA', 'REJEITADA'}
log = logging.getLogger('edgehealth.collector')


class AuthError(Exception):
    """Credential invalid or revoked: retrying cannot succeed."""


class ApiUnavailable(Exception):
    """Network error, timeout, 429 or 5xx: keep data queued and retry with backoff."""


class Api:
    def __init__(self, base_url, token, timeout=15):
        self.base = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
            'User-Agent': f'edgehealth-collector/{VERSION}'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read() or b'null')
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise AuthError('Credencial do coletor inválida ou revogada.') from None
            if error.code == 429 or error.code >= 500:
                raise ApiUnavailable(f'API respondeu HTTP {error.code}') from None
            detail = error.read()[:300].decode(errors='replace')
            raise ApiUnavailable(f'API recusou a requisição HTTP {error.code}: {detail}') from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ApiUnavailable(f'Sem conexão com a API: {type(error).__name__}') from None


class Queue:
    """Bounded on-disk queue of samples not yet confirmed by the API."""

    def __init__(self, path, limit):
        self.path = Path(path)
        self.limit = limit
        self.items = []
        self.lock = threading.Lock()
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                try:
                    self.items.append(json.loads(line))
                except ValueError:
                    log.warning('Linha inválida ignorada na fila local.')
            self._trim()

    def _trim(self):
        excess = len(self.items) - self.limit
        if excess > 0:
            # Oldest samples are discarded first; the API would reject very old samples anyway.
            del self.items[:excess]
            log.warning('Fila local cheia: %s amostras antigas descartadas.', excess)

    def _save(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(''.join(json.dumps(i) + '\n' for i in self.items), encoding='utf-8')
        os.replace(tmp, self.path)

    def add(self, items):
        with self.lock:
            self.items.extend(items)
            self._trim()
            self._save()

    def head(self, size):
        with self.lock:
            return list(self.items[:size])

    def remove(self, ids):
        with self.lock:
            self.items = [i for i in self.items if i['id'] not in ids]
            self._save()

    def __len__(self):
        return len(self.items)


def utc_now():
    return datetime.now(timezone.utc)


def measure(device, packets, timeout):
    """Returns (sample, None) or (None, error). A collector failure is never a device failure."""
    observed = utc_now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    try:
        host = ping(device['ip'], count=packets, interval=0.2, timeout=timeout, privileged=False)
    except SocketPermissionError as error:
        return None, dict(dispositivo_id=device['id'], tipo='PERMISSAO_ICMP', mensagem=str(error)[:200] or 'Sem permissão')
    except (ICMPLibError, OSError, ValueError) as error:
        return None, dict(dispositivo_id=device['id'], tipo='FALHA_COLETOR', mensagem=type(error).__name__)
    latency = round(float(host.avg_rtt), 3) if host.packets_received else None
    return dict(id=str(uuid.uuid4()), dispositivo_id=device['id'], coletada_em=observed,
                enviados=host.packets_sent, recebidos=host.packets_received, latencia_ms=latency), None


class Collector:
    def __init__(self, api, queue, workers=4, measure_fn=measure, clock=time.monotonic):
        self.api = api
        self.queue = queue
        self.workers = workers
        self.measure = measure_fn
        self.clock = clock
        self.config = None
        self.config_at = None
        self.next_due = {}
        self.pending_errors = []
        self.backoff = 0
        self.retry_at = 0
        self.stop = threading.Event()

    # --- API side ---------------------------------------------------------------------
    def api_ready(self):
        return self.clock() >= self.retry_at

    def api_failed(self, error):
        self.backoff = min(300, max(2, self.backoff * 2))
        delay = self.backoff * random.uniform(0.8, 1.2)
        self.retry_at = self.clock() + delay
        log.warning('%s. Nova tentativa em %.0f s; %s amostras na fila local.', error, delay, len(self.queue))

    def api_ok(self):
        self.backoff = 0
        self.retry_at = 0

    def refresh_config(self):
        refresh = 30 if not self.config else min(30, self.config['intervalo_segundos'])
        if self.config_at is not None and self.clock() - self.config_at < refresh:
            return
        config = self.api.call('GET', '/api/coletor/configuracao')
        server_now = datetime.fromisoformat(config['servidor_em'].replace('Z', '+00:00'))
        skew = abs((utc_now() - server_now).total_seconds())
        if skew > 60:
            log.warning('Relógio do coletor difere do servidor em %.0f s; sincronize o horário (NTP).', skew)
        ids = {d['id'] for d in config['dispositivos']}
        for device in config['dispositivos']:
            # A collection requested on the web interface arrives as an earlier proxima_coleta.
            requested = datetime.fromisoformat(device['proxima_coleta'].replace('Z', '+00:00')) <= server_now
            if requested or device['id'] not in self.next_due:
                self.next_due[device['id']] = self.clock()
        self.next_due = {k: v for k, v in self.next_due.items() if k in ids}
        if not self.config or ids != {d['id'] for d in self.config['dispositivos']}:
            log.info('Configuração recebida: %s dispositivos atribuídos.', len(ids))
        self.config, self.config_at = config, self.clock()

    def flush(self):
        size = self.config['lote_maximo'] if self.config else 100
        while len(self.queue) or self.pending_errors:
            batch = self.queue.head(size - min(len(self.pending_errors), size // 2))
            errors = self.pending_errors[:size // 2]
            response = self.api.call('POST', '/api/coletor/amostras', dict(amostras=batch, erros=errors))
            self.pending_errors = self.pending_errors[len(errors):]
            done, retry = set(), 0
            for item in response['resultados']:
                if item['resultado'] in FINAL:
                    done.add(item['id'])
                    if item['resultado'] == 'REJEITADA':
                        log.warning('Amostra rejeitada pela API: %s', item.get('motivo'))
                else:
                    retry += 1
            self.queue.remove(done)
            if retry or not batch:
                break

    def heartbeat(self):
        self.api.call('POST', '/api/coletor/heartbeat', dict(versao=VERSION, fila_pendente=len(self.queue)))

    # --- Measurement side -------------------------------------------------------------
    def due_devices(self):
        if not self.config:
            return []
        now = self.clock()
        return [d for d in self.config['dispositivos'] if self.next_due.get(d['id'], now) <= now]

    def collect(self):
        devices = self.due_devices()
        if not devices:
            return 0
        cfg = self.config
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            outcomes = list(pool.map(lambda d: self.measure(d, cfg['pacotes'], cfg['timeout_segundos']), devices))
        samples = [s for s, _ in outcomes if s]
        errors = [e for _, e in outcomes if e]
        for d in devices:
            self.next_due[d['id']] = self.clock() + cfg['intervalo_segundos']
        if samples:
            self.queue.add(samples)
        if errors:
            # Errors are reported, not queued on disk: they describe the current state only.
            self.pending_errors = (self.pending_errors + errors)[-50:]
            for e in errors:
                log.error('Coleta não executada dispositivo=%s tipo=%s', e['dispositivo_id'], e['tipo'])
        return len(samples)

    def step(self):
        if self.api_ready():
            try:
                self.refresh_config()
                self.api_ok()
            except ApiUnavailable as error:
                self.api_failed(error)
        # Measurement continues during API outages; results wait in the local queue.
        self.collect()
        if self.api_ready():
            try:
                self.flush()
                self.heartbeat()
                self.api_ok()
            except ApiUnavailable as error:
                self.api_failed(error)

    def run(self, once=False):
        log.info('Coletor EdgeHealth %s iniciado. API: %s', VERSION, self.api.base)
        while not self.stop.is_set():
            self.step()
            if once:
                break
            self.stop.wait(1)


def read_token(args):
    if args.token_file:
        return Path(args.token_file).read_text(encoding='utf-8').strip()
    token = os.getenv('EDGEHEALTH_COLLECTOR_TOKEN', '').strip()
    if not token:
        raise SystemExit('Informe a credencial em EDGEHEALTH_COLLECTOR_TOKEN ou --token-file.')
    return token


def check_url(url, allow_http):
    parsed = urllib.parse.urlparse(url)
    local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if parsed.scheme == 'https' or (parsed.scheme == 'http' and (local or allow_http)):
        return url
    raise SystemExit('Use HTTPS para a API. HTTP é aceito apenas para localhost ou com --allow-http em laboratório.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Coletor remoto EdgeHealth')
    parser.add_argument('--api-url', default=os.getenv('EDGEHEALTH_API_URL'), help='Ex.: https://edgehealth.exemplo.org')
    parser.add_argument('--token-file', default=os.getenv('EDGEHEALTH_COLLECTOR_TOKEN_FILE'))
    parser.add_argument('--queue-file', default=os.getenv('EDGEHEALTH_QUEUE_FILE', 'edgehealth-fila.jsonl'))
    parser.add_argument('--max-queue', type=int, default=int(os.getenv('EDGEHEALTH_MAX_QUEUE', '5000')))
    parser.add_argument('--workers', type=int, default=int(os.getenv('EDGEHEALTH_WORKERS', '4')))
    parser.add_argument('--once', action='store_true', help='Sincroniza, mede o que estiver vencido, envia e encerra.')
    parser.add_argument('--allow-http', action='store_true', help='Somente laboratório: aceita HTTP sem TLS.')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if not args.api_url:
        raise SystemExit('Informe --api-url ou EDGEHEALTH_API_URL.')
    if not 1 <= args.workers <= 16 or not 100 <= args.max_queue <= 100000:
        raise SystemExit('--workers deve estar entre 1 e 16 e --max-queue entre 100 e 100000.')
    collector = Collector(Api(check_url(args.api_url, args.allow_http), read_token(args)),
                          Queue(args.queue_file, args.max_queue), args.workers)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: collector.stop.set())
    try:
        collector.run(args.once)
    except AuthError as error:
        log.error('%s Gere uma nova credencial na tela Coletores.', error)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
