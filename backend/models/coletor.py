from app.extensions import db
from .base import BaseModel, utcnow


class Coletor(BaseModel):
    """Remote measurement agent running inside a company network. Never a user."""
    __tablename__ = 'coletores'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    token_prefixo = db.Column(db.String(12), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    rotacionado_em = db.Column(db.DateTime)
    revogado_em = db.Column(db.DateTime)
    ultimo_contato = db.Column(db.DateTime)
    versao = db.Column(db.String(30))
    fila_pendente = db.Column(db.Integer)
    ultimo_erro = db.Column(db.String(500))
    ultimo_erro_em = db.Column(db.DateTime)
    janela_inicio = db.Column(db.DateTime)
    janela_requisicoes = db.Column(db.Integer, nullable=False, default=0)
