from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    base_dir = Path(__file__).resolve().parent.parent
    instance_dir = base_dir / 'instance'
    instance_dir.mkdir(exist_ok=True)

    db_path = instance_dir / 'edgehealth_new.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        from app.models.dispositivo import Dispositivo
        from app.models.empresa import Empresa
        from app.models.historico_falha import HistoricoFalha
        from app.models.metrica import Metrica
        from app.models.usuario import Usuario

        db.create_all()

    from app.routes.api import api_bp
    app.register_blueprint(api_bp)

    return app