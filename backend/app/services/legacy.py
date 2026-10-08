"""One-way, read-only import of the prototype database into an empty MVP database.

Unverifiable observations remain in quarantine. They are never passed to the
collector, dashboard or diagnosis engine as real measurements.
"""
import base64
import hashlib
import secrets
import sqlite3
from pathlib import Path

from sqlalchemy import select
from werkzeug.exceptions import BadRequest
from werkzeug.security import generate_password_hash

from .. import validation as v
from ..extensions import db
from models import Empresa, Usuario, Dispositivo, RegistroLegado


def _json_value(value):
    if isinstance(value, bytes):
        return {'encoding': 'base64', 'value': base64.b64encode(value).decode('ascii')}
    return value


def import_legacy(source):
    source = Path(source).resolve(strict=True)
    destination = db.engine.url.database
    if destination and Path(destination).resolve() == source:
        raise ValueError('A origem e o destino devem ser bancos diferentes.')
    if db.session.scalar(select(Empresa.id).limit(1)) or db.session.scalar(select(RegistroLegado.id).limit(1)):
        raise ValueError('O destino deve estar vazio de empresas e importações. Nenhum dado foi alterado.')
    wal = Path(str(source) + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('A origem possui WAL. Gere uma cópia consistente com SQLite backup antes de importar.')
    with source.open('rb') as file:
        fingerprint = hashlib.file_digest(file, 'sha256').hexdigest()
    connection = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        if 'alembic_version' in names or not {'empresas', 'usuarios', 'dispositivos'} <= set(names):
            raise ValueError('A origem não é um banco do protótipo EdgeHealth reconhecido.')
        rows = {name: [dict(r) for r in connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}
    finally:
        connection.close()

    companies, devices, used_cnpj, used_email, used_ip = {}, {}, set(), set(), set()
    result = {'fonte_sha256': fingerprint, 'empresas': 0, 'usuarios': 0, 'dispositivos': 0, 'quarentena': 0, 'registros_preservados': 0}
    order = ['empresas', 'usuarios', 'dispositivos'] + sorted(set(names) - {'empresas', 'usuarios', 'dispositivos'})
    try:
        for table in order:
            for index, row in enumerate(rows[table]):
                # Plaintext passwords from the prototype must not enter the new DB.
                safe = {key: ('[REMOVIDO: credencial legada]' if any(term in key.lower() for term in ('senha', 'password', 'token', 'secret')) else _json_value(value)) for key, value in row.items()}
                tenant = companies.get(row.get('empresa_id'))
                outcome, reason = 'QUARENTENA', 'Registro histórico do protótipo; origem e método de medição não verificáveis.'
                try:
                    if table == 'empresas':
                        cnpj = v.cnpj(row.get('cnpj'))
                        name = v.string(row.get('nome_fantasia'), 'Empresa')
                        if cnpj in used_cnpj: raise ValueError('CNPJ duplicado na origem.')
                        company = Empresa(nome_fantasia=name, cnpj=cnpj)
                        db.session.add(company)
                        db.session.flush()
                        tenant = companies[row['id']] = company.id
                        used_cnpj.add(cnpj)
                    elif table == 'usuarios':
                        if not tenant: raise ValueError('Empresa ausente ou inválida na origem.')
                        name = v.string(row.get('nome'), 'Nome', 100)
                        email = v.email(row.get('email'))
                        if email in used_email: raise ValueError('E-mail duplicado na origem.')
                        db.session.add(Usuario(empresa_id=tenant, nome=name, email=email, ativo=False,
                                               papel='TECNICO', senha_hash=generate_password_hash(secrets.token_urlsafe(48))))
                        used_email.add(email)
                    elif table == 'dispositivos':
                        if not tenant: raise ValueError('Empresa ausente ou inválida na origem.')
                        address = v.ip(row.get('ip'))
                        name = v.string(row.get('nome'), 'Nome', 100)
                        kind = v.string(row.get('tipo'), 'Tipo', 50)
                        location = v.string(row.get('localizacao') or row.get('setor'), 'Localização', 150)
                        if (tenant, address) in used_ip: raise ValueError('IP ativo duplicado na empresa de origem.')
                        d = Dispositivo(empresa_id=tenant, nome=name, ip=address, tipo=kind, localizacao=location)
                        db.session.add(d)
                        db.session.flush()
                        devices[row['id']] = tenant
                        used_ip.add((tenant, address))
                    else:
                        tenant = devices.get(row.get('dispositivo_id'))
                    if table in ('empresas', 'usuarios', 'dispositivos'):
                        outcome = 'IMPORTADO'
                        reason = ('Conta desativada; operador deve definir nova senha e permissão.' if table == 'usuarios'
                                  else 'Cadastro válido importado; status e métricas não foram copiados.')
                        result[table] += 1
                except (BadRequest, ValueError, KeyError) as error:
                    reason = (error.description if isinstance(error, BadRequest) else str(error))[:500]
                if outcome == 'QUARENTENA': result['quarentena'] += 1
                db.session.add(RegistroLegado(fonte_sha256=fingerprint, tabela=table,
                    chave_original=str(row.get('id', index)), empresa_id=tenant, dados=safe,
                    resultado=outcome, motivo=reason))
                result['registros_preservados'] += 1
        db.session.commit()
        return result
    except Exception:
        db.session.rollback()
        raise
