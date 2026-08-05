from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(40), default="operador", nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    empresa = db.relationship("Empresa", back_populates="usuarios")

    def set_password(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "perfil": self.perfil,
            "ativo": self.ativo,
            "empresa_id": self.empresa_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
