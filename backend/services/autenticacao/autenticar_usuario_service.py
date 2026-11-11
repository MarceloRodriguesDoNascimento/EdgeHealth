# Caso de uso: login com e-mail e senha
from datetime import timedelta
from flask import current_app
from werkzeug.exceptions import TooManyRequests, Unauthorized
from werkzeug.security import check_password_hash, generate_password_hash
from app import validation as v
from models import LoginAttempt, Usuario, utcnow
from repositories import AutenticacaoRepository
from services.comum.hash_token import HashToken
from .criar_sessao_service import CriarSessaoService, SessaoIniciada
from .obter_perfil_service import ObterPerfilService


# Login com limite de tentativas
class AutenticarUsuarioService:
    DUMMY_HASH = generate_password_hash('unused-login-comparison')

    # Confere a senha e abre a sessão
    def executar(self, email, senha, ip):
        email = v.email(email)
        senha = v.password(senha, minimum=1)
        key = HashToken.sha256((ip or '') + '|' + email)
        AutenticacaoRepository.remover_tentativas_anteriores(utcnow() - timedelta(seconds=current_app.config['LOGIN_WINDOW_SECONDS']))
        if AutenticacaoRepository.contar_tentativas(key) >= current_app.config['LOGIN_MAX_ATTEMPTS']:
            raise TooManyRequests('Muitas tentativas. Aguarde 15 minutos.')
        user = Usuario.buscar_um_por(email=email)
        valid = check_password_hash(user.senha_hash if user else self.DUMMY_HASH, senha)
        if not user or not user.ativo or not valid:
            LoginAttempt(key=key).salvar()
            raise Unauthorized('E-mail ou senha inválidos.')
        AutenticacaoRepository.remover_tentativas(key)
        corpo = ObterPerfilService().executar(user)
        token, csrf = CriarSessaoService().executar(user)
        return SessaoIniciada(corpo, token, csrf)
