from flask import current_app
from werkzeug.exceptions import BadRequest
from models import utcnow
from .obter_perfil_service import ObterPerfilService


class AceitarTermosService:
    """Acceptance of the current Terms of Use (and acknowledgement of the Privacy Notice)."""

    @staticmethod
    def registrar_aceite(usuario):
        usuario.termos_versao = current_app.config['TERMS_VERSION']
        usuario.termos_aceitos_em = utcnow()

    def executar(self, usuario, aceite):
        if aceite is not True:
            raise BadRequest('Confirme o aceite dos Termos de Uso.')
        self.registrar_aceite(usuario)
        usuario.atualizar()
        return ObterPerfilService().executar(usuario)
