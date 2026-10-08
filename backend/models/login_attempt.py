from app.extensions import db
from .base import BaseModel, utcnow


class LoginAttempt(BaseModel):
    """Failed login counted by the rate limit (key = SHA-256 of IP + e-mail)."""
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
