from sqlalchemy import CheckConstraint
from app.extensions import db
from .base import BaseModel, DecimalText, utcnow


class Impacto(BaseModel):
    __tablename__ = 'impactos'
    id = db.Column(db.Integer, primary_key=True)
    falha_id = db.Column(db.Integer, db.ForeignKey('falhas.id', ondelete='RESTRICT'), nullable=False, unique=True)
    usuarios_afetados = db.Column(db.Integer)
    origem = db.Column(db.String(30), nullable=False, default='NAO_INFORMADO')
    observacao = db.Column(db.String(500))
    atualizado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    custos_diretos = db.Column(DecimalText())  # technician, parts, penalties (R$)
    __table_args__ = (CheckConstraint('usuarios_afetados IS NULL OR usuarios_afetados >= 0', name='usuarios'),)
