from datetime import datetime, timezone

from app import db


class Dispositivo(db.Model):
    __tablename__ = "dispositivos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    identificador = db.Column(db.String(120), unique=True, nullable=False, index=True)
    tipo = db.Column(db.String(80), default="sensor", nullable=False)
    localizacao = db.Column(db.String(160))
    status = db.Column(db.String(30), default="offline", nullable=False)
    ultimo_ping = db.Column(db.DateTime)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    empresa = db.relationship("Empresa", back_populates="dispositivos")
    metricas = db.relationship(
        "Metrica",
        back_populates="dispositivo",
        cascade="all, delete-orphan",
    )
    historico_falhas = db.relationship(
        "HistoricoFalha",
        back_populates="dispositivo",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "identificador": self.identificador,
            "tipo": self.tipo,
            "localizacao": self.localizacao,
            "status": self.status,
            "ultimo_ping": self.ultimo_ping.isoformat() if self.ultimo_ping else None,
            "empresa_id": self.empresa_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
