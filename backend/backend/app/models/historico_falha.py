from datetime import datetime

from app import db


class HistoricoFalha(db.Model):
    __tablename__ = "historico_falhas"

    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id"), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "dispositivo_id": self.dispositivo_id,
            "descricao": self.descricao,
            "criada_em": self.criada_em.isoformat() if self.criada_em else None,
        }
