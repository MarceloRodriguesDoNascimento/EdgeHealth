# Controller da tela Coletores (administração)
from services.coletores.cadastrar_coletor_service import CadastrarColetorService
from services.coletores.listar_coletores_service import ListarColetoresService
from services.coletores.revogar_coletor_service import RevogarColetorService
from services.coletores.rotacionar_credencial_coletor_service import RotacionarCredencialColetorService
from .base_controller import BaseController


# Rotas de administração dos coletores
class ColetorController(BaseController):
    # GET /api/coletores: lista os coletores da empresa
    def listar(self):
        return self.resposta(ListarColetoresService().executar(self.empresa_id()))

    # POST /api/coletores: cria coletor e devolve a credencial
    def cadastrar(self):
        dados = self.payload(['nome'], ['nome'])
        return self.resposta(CadastrarColetorService().executar(self.empresa_id(), dados['nome']), 201)

    # POST /api/coletores/<id>/rotacionar: gera credencial nova
    def rotacionar(self, id):
        self.payload([])
        return self.resposta(RotacionarCredencialColetorService().executar(self.empresa_id(), id))

    # POST /api/coletores/<id>/revogar: desativa o coletor
    def revogar(self, id):
        self.payload([])
        return self.resposta(RevogarColetorService().executar(self.empresa_id(), id))
