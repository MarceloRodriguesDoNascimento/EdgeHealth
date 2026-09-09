import hashlib
import secrets
from datetime import timedelta
from functools import wraps
from flask import current_app, g, request
from sqlalchemy import delete, select, func
from werkzeug.exceptions import Forbidden, Unauthorized, TooManyRequests
from werkzeug.security import check_password_hash, generate_password_hash
from ..extensions import db
from ..models import AuthSession, LoginAttempt, Usuario, utcnow

# Equal-cost verification even when an account is absent.
DUMMY_HASH = generate_password_hash('unused-login-comparison')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def issue_session(user, response):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(hours=current_app.config['SESSION_HOURS'])
    db.session.add(AuthSession(id=digest(token), usuario_id=user.id, csrf_hash=digest(csrf), expires_at=expires))
    db.session.execute(delete(AuthSession).where(AuthSession.expires_at < utcnow()))
    db.session.commit()
    opts = dict(secure=current_app.config['SESSION_COOKIE_SECURE'], samesite='Lax', path='/',
                max_age=current_app.config['SESSION_HOURS'] * 3600)
    response.set_cookie(current_app.config['SESSION_COOKIE_NAME'], token, httponly=True, **opts)
    response.set_cookie('edgehealth_csrf', csrf, httponly=False, **opts)
    return response


def login(email, password):
    key = digest((request.remote_addr or '') + '|' + email)
    cutoff = utcnow() - timedelta(seconds=current_app.config['LOGIN_WINDOW_SECONDS'])
    db.session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
    count = db.session.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.key == key))
    if count >= current_app.config['LOGIN_MAX_ATTEMPTS']:
        raise TooManyRequests('Muitas tentativas. Aguarde 15 minutos.')
    user = db.session.scalar(select(Usuario).where(Usuario.email == email))
    valid = check_password_hash(user.senha_hash if user else DUMMY_HASH, password)
    if not user or not user.ativo or not valid:
        db.session.add(LoginAttempt(key=key))
        db.session.commit()
        raise Unauthorized('E-mail ou senha inválidos.')
    db.session.execute(delete(LoginAttempt).where(LoginAttempt.key == key))
    return user


def require_auth(admin=False):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            token = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'], '')
            session = db.session.get(AuthSession, digest(token)) if token else None
            user = db.session.get(Usuario, session.usuario_id) if session else None
            if not session or session.expires_at <= utcnow() or not user or not user.ativo:
                raise Unauthorized('Sessão expirada. Entre novamente.')
            if admin and user.papel != 'ADMIN':
                raise Forbidden('Esta operação exige um administrador da empresa.')
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                csrf = request.headers.get('X-CSRF-Token', '')
                if not csrf or not secrets.compare_digest(digest(csrf), session.csrf_hash):
                    raise Forbidden('Requisição inválida. Atualize a página e tente novamente.')
            g.user, g.auth_session = user, session
            return fn(*args, **kwargs)
        return wrapped
    return decorate
