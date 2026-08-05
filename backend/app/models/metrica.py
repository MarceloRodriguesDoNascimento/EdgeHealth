from datetime import datetime, timezone

from app import db


class Metrica(db.Model):
    __tablename__ = "metricas"

    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(
        db.Integer,
        db.ForeignKey("dispositivos.id"),
        nullable=False,
        index=True,
    )
    cpu_percent = db.Column(db.Float)
    memoria_percent = db.Column(db.Float)
    disco_percent = db.Column(db.Float)
    temperatura_c = db.Column(db.Float)
    latencia_ms = db.Column(db.Float)
    coletada_em = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    dispositivo = db.relationship("Dispositivo", back_populates="metricas")

    def to_dict(self):
        return {
            "id": self.id,
            "dispositivo_id": self.dispositivo_id,
            "cpu_percent": self.cpu_percent,
            "memoria_percent": self.memoria_percent,
            "disco_percent": self.disco_percent,
            "temperatura_c": self.temperatura_c,
            "latencia_ms": self.latencia_ms,
            "coletada_em": self.coletada_em.isoformat() if self.coletada_em else None,
        }
