from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app(config_object: str | None = None) -> Flask:
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)
    else:
        app.config.from_object("app.config.Config")

    CORS(app)
    db.init_app(app)

    from app import models  # noqa: F401
    from app.routes.api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/")
    def index():
        return {
            "app": "EdgeHealth API",
            "healthcheck": "/api/health",
        }

    return app
