# Caso de uso: recuperar uma conta pelo terminal
from werkzeug.security import generate_password_hash
from app import validation as v
from models import Usuario
from repositories import AutenticacaoRepository


# Ativação de usuário
class AtivarUsuarioService:
    # Define nova senha e reativa a conta
    def executar(self, email, senha, admin=False):
        user = Usuario.buscar_um_por(email=email.strip().lower())
        if not user:
            raise ValueError('Conta não encontrada. Revise os registros em quarentena.')
        new_password = v.password(senha)
        user.senha_hash = generate_password_hash(new_password)
        user.ativo = True
        user.papel = 'ADMIN' if admin else user.papel
        AutenticacaoRepository.remover_sessoes_do_usuario(user.id)
        user.atualizar()
