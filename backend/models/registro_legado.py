from sqlalchemy import CheckConstraint
from app.extensions import db
from .base import BaseModel, utcnow


class RegistroLegado(BaseModel):
    """Quarantined source records, never mixed with measured monitoring history."""
    __tablename__ = 'registros_legados'
    id = db.Column(db.Integer, primary_key=True)
    fonte_sha256 = db.Column(db.String(64), nullable=False)
    tabela = db.Column(db.String(100), nullable=False)
    chave_original = db.Column(db.String(100), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), index=True)
    dados = db.Column(db.JSON, nullable=False)
    resultado = db.Column(db.String(30), nullable=False)
    motivo = db.Column(db.String(500), nullable=False)
    importado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint('fonte_sha256', 'tabela', 'chave_original', name='uq_registro_legado_origem'),
        CheckConstraint("resultado IN ('IMPORTADO','QUARENTENA')", name='resultado'),
    )
