"""Authentication decorators of the HTTP layer and the session cookies.

The checks themselves live in the services; here only the request is read (cookie, headers,
method) and the authenticated user/collector is placed in flask.g for the controllers.
"""
from functools import wraps
from flask import current_app, g, request
from services.autenticacao.validar_sessao_service import ValidarSessaoService
from services.coletor_api.autenticar_coletor_service import AutenticarColetorService

CSRF_COOKIE = 'edgehealth_csrf'


def require_auth(admin=False, terms=True):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            g.user, g.auth_session = ValidarSessaoService().executar(
                token=request.cookies.get(current_app.config['SESSION_COOKIE_NAME'], ''),
                csrf=request.headers.get('X-CSRF-Token', ''), metodo=request.method, admin=admin, termos=terms)
            return fn(*args, **kwargs)
        return wrapped
    return decorate


def require_collector(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        g.collector = AutenticarColetorService().executar(header[7:].strip() if header.startswith('Bearer ') else '')
        request.max_content_length = current_app.config['COLLECTOR_MAX_CONTENT_LENGTH']
        return fn(*args, **kwargs)
    return wrapped


def set_session_cookies(response, token, csrf):
    cfg = current_app.config
    opts = dict(secure=cfg['SESSION_COOKIE_SECURE'], samesite='Lax', path='/', max_age=cfg['SESSION_HOURS'] * 3600)
    response.set_cookie(cfg['SESSION_COOKIE_NAME'], token, httponly=True, **opts)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, **opts)
    return response


def clear_session_cookies(response):
    response.delete_cookie(current_app.config['SESSION_COOKIE_NAME'], path='/')
    response.delete_cookie(CSRF_COOKIE, path='/')
    return response
