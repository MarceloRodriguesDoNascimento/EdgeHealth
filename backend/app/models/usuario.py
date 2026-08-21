from app import db

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(128), nullable=False) # Lembre-se: no controller, guarde o hash da senha!
    
    # FK para conectar o usuário à empresa
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)

    def __init__(self, nome, email, senha, empresa_id):
        self.nome = nome
        self.email = email
        self.senha = senha
        self.empresa_id = empresa_id

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'empresa_id': self.empresa_id,
        }

    def __repr__(self):
        return f'<Usuario {self.nome}>'
