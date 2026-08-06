from app import db

class Empresa(db.Model):
    __tablename__ = 'empresas'

    id = db.Column(db.Integer, primary_key=True)
    nome_fantasia = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, nullable=False)
    
    # Relações (opcional, mas recomendado para facilitar consultas)
    # Uma empresa tem vários dispositivos e vários usuários
    dispositivos = db.relationship('Dispositivo', backref='empresa', lazy=True)
    usuarios = db.relationship('Usuario', backref='empresa', lazy=True)

    def __init__(self, nome_fantasia, cnpj):
        self.nome_fantasia = nome_fantasia
        self.cnpj = cnpj

    def to_dict(self):
        return {
            'id': self.id,
            'nome_fantasia': self.nome_fantasia,
            'cnpj': self.cnpj,
        }

    def __repr__(self):
        return f'<Empresa {self.nome_fantasia}>'
