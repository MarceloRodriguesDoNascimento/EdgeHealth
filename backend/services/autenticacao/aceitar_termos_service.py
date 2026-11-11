# Caso de uso: aceitar os Termos de Uso
from flask import current_app
from werkzeug.exceptions import BadRequest
from models import utcnow
from .obter_perfil_service import ObterPerfilService


# Registra o aceite dos termos
class AceitarTermosService:
    # Marca versão e data do aceite
    @staticmethod
    def registrar_aceite(usuario):
        usuario.termos_versao = current_app.config['TERMS_VERSION']
        usuario.termos_aceitos_em = utcnow()

    # Valida e grava o aceite
    def executar(self, usuario, aceite):
        if aceite is not True:
            raise BadRequest('Confirme o aceite dos Termos de Uso.')
        self.registrar_aceite(usuario)
        usuario.atualizar()
        return ObterPerfilService().executar(usuario)
