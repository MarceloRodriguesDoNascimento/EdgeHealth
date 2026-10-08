from flask import current_app


class ConsultarTermosService:
    """Current version of the Terms of Use (public)."""

    def executar(self):
        return dict(versao=current_app.config['TERMS_VERSION'])
