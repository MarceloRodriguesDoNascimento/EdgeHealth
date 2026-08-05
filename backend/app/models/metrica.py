from datetime import datetime

from app import db


class Metrica(db.Model):
    __tablename__ = "metricas"

    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id"), nullable=False)
    tipo = db.Column(db.String(80), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "dispositivo_id": self.dispositivo_id,
            "tipo": self.tipo,
            "valor": self.valor,
            "criada_em": self.criada_em.isoformat() if self.criada_em else None,
        }
