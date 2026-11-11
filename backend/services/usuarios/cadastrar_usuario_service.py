# Caso de uso: cadastrar usuário
from models import Usuario
from services.comum.serializador import Serializador
from .dados_usuario import DadosUsuario


# Cadastro de usuário
class CadastrarUsuarioService:
    # Valida e cria a conta
    def executar(self, solicitante, dados):
        user = Usuario(empresa_id=solicitante.empresa_id)
        DadosUsuario.aplicar(user, dados, None, solicitante.id)
        user.papel = user.papel or 'TECNICO'
        user.salvar()
        return Serializador.usuario(user)
