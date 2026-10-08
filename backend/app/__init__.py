import logging
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from .config import Config
from .extensions import db, migrate

def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if app.config['TRUST_PROXY']:
        # Behind exactly N trusted reverse proxies (TLS termination): real client IP and scheme.
        from werkzeug.middleware.proxy_fix import ProxyFix
        hops = app.config['TRUST_PROXY']
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)
    db.init_app(app)
    import models  # noqa: F401  (registers every table in the metadata)
    migrate.init_app(app, db, render_as_batch=True)
    from .api import api
    from .cli import register_cli
    app.register_blueprint(api)
    register_cli(app)

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        return jsonify(erro='Operação conflitante ou referência inválida. Verifique os dados.'), 409

    @app.errorhandler(HTTPException)
    def http_error(error):
        db.session.rollback()
        return jsonify(erro=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        db.session.rollback()
        app.logger.exception('Erro não previsto durante a requisição')
        return jsonify(erro='Não foi possível concluir a operação.'), 500

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        if response.mimetype == 'application/json':
            response.headers['Cache-Control'] = 'no-store'
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.get('/')
    @app.get('/<path:path>')
    def frontend(path='index.html'):
        if path.startswith('api/'):
            return jsonify(erro='Rota não encontrada.'), 404
        return send_from_directory(app.config['FRONTEND_DIST'], path)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    if not app.config['SESSION_COOKIE_SECURE'] and not app.testing:
        app.logger.warning('COOKIE_SECURE=false: use somente em HTTP local. Em hospedagem com HTTPS defina COOKIE_SECURE=true.')
    return app
