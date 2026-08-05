from app import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "empresa_id": self.empresa_id,
        }
