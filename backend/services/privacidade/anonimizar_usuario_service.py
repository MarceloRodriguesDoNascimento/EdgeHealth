import secrets
from werkzeug.security import generate_password_hash
from models import Empresa, Usuario, utcnow
from repositories import AutenticacaoRepository, UsuarioRepository


class AnonimizarUsuarioService:
    """Data-subject request: removes name/e-mail of an account while keeping company history."""

    def executar(self, email):
        user = Usuario.buscar_um_por(email=email)
        if not user:
            raise ValueError('Conta não encontrada.')
        if user.papel == 'ADMIN' and user.ativo:
            if UsuarioRepository.contar_admins_ativos(user.empresa_id) <= 1:
                raise ValueError('É o único administrador ativo. Promova outro administrador antes de anonimizar.')
        company = Empresa.buscar_por_id(user.empresa_id)
        if company.email == user.email:
            company.email = None
        user.nome = 'Usuário anonimizado'
        user.email = f'anonimizado-{user.id}@anonimizado.invalid'
        user.senha_hash = generate_password_hash(secrets.token_urlsafe(32))
        user.ativo = False
        user.anonimizado_em = utcnow()
        AutenticacaoRepository.remover_sessoes_do_usuario(user.id)
        user.atualizar()
