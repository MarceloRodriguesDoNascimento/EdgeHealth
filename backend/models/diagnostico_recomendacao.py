from app.extensions import db
from .base import BaseModel


class DiagnosticoRecomendacao(BaseModel):
    __tablename__ = 'diagnostico_recomendacoes'
    diagnostico_id = db.Column(db.Integer, db.ForeignKey('diagnosticos.id', ondelete='CASCADE'), primary_key=True)
    recomendacao_id = db.Column(db.Integer, db.ForeignKey('recomendacoes.id', ondelete='RESTRICT'), primary_key=True)
