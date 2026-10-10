import secrets
from dataclasses import dataclass
from datetime import timedelta
from flask import current_app
from models import AuthSession, utcnow
from repositories import AutenticacaoRepository, Transacao
from services.comum.hash_token import HashToken


@dataclass(frozen=True)
class SessaoIniciada:
    """Response body of a successful login/registration and the credentials for the cookies."""
    corpo: dict
    token: str
    csrf: str


class CriarSessaoService:
    """Opens a session for the user (only hashes are stored) and confirms the transaction."""

    def executar(self, usuario):
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        expires = utcnow() + timedelta(hours=current_app.config['SESSION_HOURS'])
        AuthSession(id=HashToken.sha256(token), usuario_id=usuario.id, csrf_hash=HashToken.sha256(csrf),
                    expires_at=expires).salvar(commit=False)
        AutenticacaoRepository.remover_sessoes_expiradas(utcnow())
        Transacao.confirmar()
        return token, csrf
