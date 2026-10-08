from app.extensions import db
from .base import BaseModel


class AuthSession(BaseModel):
    """Login session of a user (only the SHA-256 of the cookie token is stored)."""
    __tablename__ = 'auth_sessions'
    id = db.Column(db.String(64), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, index=True)
    csrf_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
