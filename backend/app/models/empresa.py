from datetime import datetime, timezone

from app import db


class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    usuarios = db.relationship(
        "Usuario",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    dispositivos = db.relationship(
        "Dispositivo",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "cnpj": self.cnpj,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
