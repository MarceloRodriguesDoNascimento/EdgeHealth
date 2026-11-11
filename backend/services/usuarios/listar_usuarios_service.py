# Caso de uso: listar usuários
from repositories import UsuarioRepository
from services.comum.serializador import Serializador


# Lista de usuários
class ListarUsuariosService:
    # Devolve os usuários da empresa
    def executar(self, empresa_id):
        return [Serializador.usuario(u) for u in UsuarioRepository.listar_da_empresa(empresa_id)]
