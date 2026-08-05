from datetime import datetime, timezone

from app import db


class HistoricoFalha(db.Model):
    __tablename__ = "historico_falhas"

    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(
        db.Integer,
        db.ForeignKey("dispositivos.id"),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String(80), default="conectividade", nullable=False)
    descricao = db.Column(db.Text)
    resolvida = db.Column(db.Boolean, default=False, nullable=False)
    ocorreu_em = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolvida_em = db.Column(db.DateTime)

    dispositivo = db.relationship("Dispositivo", back_populates="historico_falhas")

    def to_dict(self):
        return {
            "id": self.id,
            "dispositivo_id": self.dispositivo_id,
            "tipo": self.tipo,
            "descricao": self.descricao,
            "resolvida": self.resolvida,
            "ocorreu_em": self.ocorreu_em.isoformat() if self.ocorreu_em else None,
            "resolvida_em": self.resolvida_em.isoformat() if self.resolvida_em else None,
        }
