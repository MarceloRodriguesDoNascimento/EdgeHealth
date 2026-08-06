from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///edgehealth.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        # Importa os models para criar as tabelas
        from app.models.dispositivo import Dispositivo
        from app.models.empresa import Empresa
        from app.models.historico_falha import HistoricoFalha
        from app.models.metrica import Metrica
        from app.models.usuario import Usuario
        
        db.create_all()

    # Registra o Blueprint das rotas da API
    from app.routes.api import api_bp
    app.register_blueprint(api_bp)

    return app