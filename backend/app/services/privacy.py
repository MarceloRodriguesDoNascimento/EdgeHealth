"""Retention, data-subject requests and backups (LGPD technical measures)."""
import os
import secrets
import sqlite3
from datetime import timedelta
from sqlalchemy import delete, func, select
from werkzeug.security import generate_password_hash
from ..extensions import db
from models import AuthSession, Empresa, LoginAttempt, Metrica, Usuario, utcnow


def purge_history(days, dry_run=False):
    """Removes raw samples older than the retention period.

    Incidents, impacts and diagnoses are kept: diagnoses already store the values of
    the samples they cite, so the explanation survives the purge of raw samples.
    """
    now = utcnow()
    cutoff = now - timedelta(days=days)
    targets = [(Metrica, Metrica.coletada_em < cutoff),
               (AuthSession, AuthSession.expires_at < now),
               (LoginAttempt, LoginAttempt.created_at < now - timedelta(days=1))]
    result = dict(limite=cutoff.isoformat() + 'Z', simulacao=dry_run)
    for model, condition in targets:
        result[model.__tablename__] = db.session.scalar(select(func.count()).select_from(model).where(condition))
        if not dry_run:
            db.session.execute(delete(model).where(condition))
    db.session.commit()
    return result


def anonymize_user(email):
    user = db.session.scalar(select(Usuario).where(Usuario.email == email))
    if not user:
        raise ValueError('Conta não encontrada.')
    if user.papel == 'ADMIN' and user.ativo:
        admins = db.session.scalar(select(func.count()).select_from(Usuario).where(
            Usuario.empresa_id == user.empresa_id, Usuario.papel == 'ADMIN', Usuario.ativo.is_(True)))
        if admins <= 1:
            raise ValueError('É o único administrador ativo. Promova outro administrador antes de anonimizar.')
    company = db.session.get(Empresa, user.empresa_id)
    if company.email == user.email:
        company.email = None
    user.nome = 'Usuário anonimizado'
    user.email = f'anonimizado-{user.id}@anonimizado.invalid'
    user.senha_hash = generate_password_hash(secrets.token_urlsafe(32))
    user.ativo = False
    user.anonimizado_em = utcnow()
    db.session.execute(delete(AuthSession).where(AuthSession.usuario_id == user.id))
    db.session.commit()


def backup_sqlite(output):
    url = db.engine.url
    if url.get_backend_name() != 'sqlite' or not url.database:
        raise ValueError('O comando de backup suporta somente SQLite; use a ferramenta do banco utilizado.')
    if os.path.exists(output):
        raise ValueError('O arquivo de destino já existe; escolha outro nome.')
    source = sqlite3.connect(url.database)
    target = sqlite3.connect(output)
    try:
        with target:
            source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('A cópia não passou na verificação de integridade.')
    finally:
        target.close()
        source.close()
