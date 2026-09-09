import ipaddress
import re
from datetime import datetime, timezone, timedelta
from flask import request
from werkzeug.exceptions import BadRequest


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


def string(value, field, maximum=150, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise BadRequest(f'{field}: informe entre {minimum} e {maximum} caracteres.')
    return value.strip()


def email(value):
    value = string(value, 'E-mail', 254).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise BadRequest('E-mail inválido.')
    return value


def password(value, minimum=10):
    if not isinstance(value, str) or not minimum <= len(value) <= 128:
        raise BadRequest(f'A senha deve ter entre {minimum} e 128 caracteres.')
    return value


def cnpj(value):
    value = string(value, 'CNPJ', 18).upper()
    if re.search(r'[^A-Z0-9./\-]', value):
        raise BadRequest('CNPJ inválido.')
    value = re.sub(r'[./\-]', '', value)
    if not re.fullmatch(r'[A-Z0-9]{12}[0-9]{2}', value) or len(set(value)) == 1:
        raise BadRequest('CNPJ inválido.')
    # Receita Federal's numeric and alphanumeric DV algorithm: ASCII minus 48.
    for n, weights in [(12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])]:
        rem = sum((ord(d)-48) * w for d, w in zip(value[:n], weights)) % 11
        if int(value[n]) != (0 if rem < 2 else 11-rem):
            raise BadRequest('Dígitos verificadores do CNPJ inválidos.')
    return value


def ip(value):
    try:
        parsed = ipaddress.ip_address(string(value, 'IP', 45))
        if parsed.is_multicast or parsed.is_unspecified or '%' in str(value):
            raise ValueError()
        return str(parsed)
    except ValueError:
        raise BadRequest('Informe um endereço IPv4 ou IPv6 de um dispositivo.')


def integer(value, field, low=0, high=1000000):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise BadRequest(f'{field}: informe um inteiro entre {low} e {high}.')
    return value


def query_int(name, default=None, low=1, high=2147483647):
    raw = request.args.get(name)
    if raw is None or raw == '':
        return default
    try:
        result = int(raw)
    except ValueError:
        raise BadRequest(f'{name} inválido.')
    return integer(result, name, low, high)


def period(default_days=None):
    def parse(raw, end=False):
        if not raw:
            return None
        try:
            value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            if len(raw) == 10 and end:
                value += timedelta(days=1)
            if value.tzinfo:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        except ValueError:
            raise BadRequest('Período inválido. Use datas ISO 8601.')
    start = parse(request.args.get('inicio'))
    end = parse(request.args.get('fim'), True)
    if not start and default_days:
        start = (end or datetime.now(timezone.utc).replace(tzinfo=None)) - timedelta(days=default_days)
    if start and end and start >= end:
        raise BadRequest('O início deve ser anterior ao fim.')
    return start, end
