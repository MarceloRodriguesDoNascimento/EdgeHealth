# Controller da equipe (usuários da empresa)
from services.usuarios.atualizar_usuario_service import AtualizarUsuarioService
from services.usuarios.cadastrar_usuario_service import CadastrarUsuarioService
from services.usuarios.listar_usuarios_service import ListarUsuariosService
from .base_controller import BaseController


# Rotas de usuários
class UsuarioController(BaseController):
    # GET /api/usuarios: usuários da empresa
    def listar(self):
        return self.resposta(ListarUsuariosService().executar(self.empresa_id()))

    # POST /api/usuarios: cria uma conta
    def cadastrar(self):
        dados = self.payload(['nome', 'email', 'senha', 'papel'], ['nome', 'email', 'senha'])
        return self.resposta(CadastrarUsuarioService().executar(self.usuario(), dados), 201)

    # PUT /api/usuarios/<id>: edita ou ativa/desativa uma conta
    def atualizar(self, id):
        dados = self.payload(['nome', 'email', 'senha', 'papel', 'ativo'])
        return self.resposta(AtualizarUsuarioService().executar(self.usuario(), id, dados))
