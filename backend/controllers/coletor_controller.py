from services.coletores.cadastrar_coletor_service import CadastrarColetorService
from services.coletores.listar_coletores_service import ListarColetoresService
from services.coletores.revogar_coletor_service import RevogarColetorService
from services.coletores.rotacionar_credencial_coletor_service import RotacionarCredencialColetorService
from .base_controller import BaseController


class ColetorController(BaseController):
    """Administration of the company's remote collectors (user session)."""

    def listar(self):
        return self.resposta(ListarColetoresService().executar(self.empresa_id()))

    def cadastrar(self):
        dados = self.payload(['nome'], ['nome'])
        return self.resposta(CadastrarColetorService().executar(self.empresa_id(), dados['nome']), 201)

    def rotacionar(self, id):
        self.payload([])
        return self.resposta(RotacionarCredencialColetorService().executar(self.empresa_id(), id))

    def revogar(self, id):
        self.payload([])
        return self.resposta(RevogarColetorService().executar(self.empresa_id(), id))
