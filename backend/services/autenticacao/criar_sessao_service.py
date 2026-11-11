# Caso de uso: abrir uma sessão de login
import secrets
from dataclasses import dataclass
from datetime import timedelta
from flask import current_app
from models import AuthSession, utcnow
from repositories import AutenticacaoRepository, Transacao
from services.comum.hash_token import HashToken


# Resultado: resposta e tokens para os cookies
@dataclass(frozen=True)
class SessaoIniciada:
    corpo: dict
    token: str
    csrf: str


# Cria a sessão do usuário
class CriarSessaoService:
    # Gera os tokens e grava a sessão
    def executar(self, usuario):
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        expires = utcnow() + timedelta(hours=current_app.config['SESSION_HOURS'])
        AuthSession(id=HashToken.sha256(token), usuario_id=usuario.id, csrf_hash=HashToken.sha256(csrf),
                    expires_at=expires).salvar(commit=False)
        AutenticacaoRepository.remover_sessoes_expiradas(utcnow())
        Transacao.confirmar()
        return token, csrf
