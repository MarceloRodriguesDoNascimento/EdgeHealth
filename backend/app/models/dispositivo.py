from app import db


class Dispositivo(db.Model):
    __tablename__ = "dispositivos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    identificador = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(40), default="offline", nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "identificador": self.identificador,
            "status": self.status,
            "empresa_id": self.empresa_id,
        }
