from services.usuarios.atualizar_usuario_service import AtualizarUsuarioService
from services.usuarios.cadastrar_usuario_service import CadastrarUsuarioService
from services.usuarios.listar_usuarios_service import ListarUsuariosService
from .base_controller import BaseController


class UsuarioController(BaseController):
    def listar(self):
        return self.resposta(ListarUsuariosService().executar(self.empresa_id()))

    def cadastrar(self):
        dados = self.payload(['nome', 'email', 'senha', 'papel'], ['nome', 'email', 'senha'])
        return self.resposta(CadastrarUsuarioService().executar(self.usuario(), dados), 201)

    def atualizar(self, id):
        dados = self.payload(['nome', 'email', 'senha', 'papel', 'ativo'])
        return self.resposta(AtualizarUsuarioService().executar(self.usuario(), id, dados))
