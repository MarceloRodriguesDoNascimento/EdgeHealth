from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    db.init_app(app)

    from app import models  # noqa: F401
    from app.routes.api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    return app
