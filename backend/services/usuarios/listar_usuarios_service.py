from repositories import UsuarioRepository
from services.comum.serializador import Serializador


class ListarUsuariosService:
    def executar(self, empresa_id):
        return [Serializador.usuario(u) for u in UsuarioRepository.listar_da_empresa(empresa_id)]
