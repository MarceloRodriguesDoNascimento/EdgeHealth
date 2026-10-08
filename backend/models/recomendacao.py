from app.extensions import db
from .base import BaseModel


class Recomendacao(BaseModel):
    __tablename__ = 'recomendacoes'
    id = db.Column(db.Integer, primary_key=True)
    regra = db.Column(db.String(50), nullable=False)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    titulo = db.Column(db.String(150), nullable=False)
    acao = db.Column(db.Text, nullable=False)
