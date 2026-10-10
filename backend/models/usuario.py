from sqlalchemy import CheckConstraint
from app.extensions import db
from .base import BaseModel, utcnow


class Usuario(BaseModel):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True)
    senha_hash = db.Column(db.String(512), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default='TECNICO')
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criada_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    # Acceptance of the Terms of Use and acknowledgement of the Privacy Notice (not consent).
    termos_versao = db.Column(db.String(20))
    termos_aceitos_em = db.Column(db.DateTime)
    anonimizado_em = db.Column(db.DateTime)
    __table_args__ = (CheckConstraint("papel IN ('ADMIN','TECNICO')", name='papel'),)
