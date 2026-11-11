# Model das sessões de login abertas
from app.extensions import db
from .base import BaseModel


# Tabela auth_sessions: sessão de login de um usuário
class AuthSession(BaseModel):
    __tablename__ = 'auth_sessions'
    id = db.Column(db.String(64), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, index=True)
    csrf_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
