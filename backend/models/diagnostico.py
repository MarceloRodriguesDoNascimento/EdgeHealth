from sqlalchemy import CheckConstraint
from app.extensions import db
from .base import BaseModel, utcnow


class Diagnostico(BaseModel):
    __tablename__ = 'diagnosticos'
    id = db.Column(db.Integer, primary_key=True)
    falha_id = db.Column(db.Integer, db.ForeignKey('falhas.id', ondelete='RESTRICT'), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=False)
    causas = db.Column(db.JSON, nullable=False, default=list)
    evidencias = db.Column(db.JSON, nullable=False, default=dict)
    estado = db.Column(db.String(30), nullable=False)
    analisado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    versao_regras = db.Column(db.String(20), nullable=False, default='1.0')
    __table_args__ = (CheckConstraint("estado IN ('DISPONIVEL','EVIDENCIA_INSUFICIENTE')", name='estado'),)
