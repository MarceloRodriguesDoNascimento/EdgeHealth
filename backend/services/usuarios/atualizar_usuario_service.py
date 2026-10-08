from werkzeug.exceptions import NotFound
from repositories import AutenticacaoRepository, UsuarioRepository
from services.comum.serializador import Serializador
from .dados_usuario import DadosUsuario


class AtualizarUsuarioService:
    """Edits a user of the company; a new password, role change or deactivation ends their sessions."""

    def executar(self, solicitante, id, dados):
        user = UsuarioRepository.buscar_da_empresa(solicitante.empresa_id, id)
        if not user: raise NotFound('Usuário não encontrado.')
        DadosUsuario.aplicar(user, dados, id, solicitante.id)
        if 'senha' in dados or dados.get('ativo') is False or 'papel' in dados:
            AutenticacaoRepository.remover_sessoes_do_usuario(user.id)
        user.atualizar()
        return Serializador.usuario(user)
