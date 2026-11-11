# Caso de uso: consultar a versão dos termos
from flask import current_app


# Versão atual dos termos
class ConsultarTermosService:
    # Devolve a versão
    def executar(self):
        return dict(versao=current_app.config['TERMS_VERSION'])
