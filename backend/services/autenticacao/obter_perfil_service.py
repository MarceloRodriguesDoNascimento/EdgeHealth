from models import Empresa
from services.comum.serializador import Serializador


class ObterPerfilService:
    """Signed-in user and their company."""

    def executar(self, usuario):
        return dict(usuario=Serializador.usuario(usuario),
                    empresa=Serializador.empresa(Empresa.buscar_por_id(usuario.empresa_id)))
