# Caso de uso: dados do usuário logado
from models import Empresa
from services.comum.serializador import Serializador


# Perfil do usuário
class ObterPerfilService:
    # Devolve usuário e empresa em JSON
    def executar(self, usuario):
        return dict(usuario=Serializador.usuario(usuario),
                    empresa=Serializador.empresa(Empresa.buscar_por_id(usuario.empresa_id)))
