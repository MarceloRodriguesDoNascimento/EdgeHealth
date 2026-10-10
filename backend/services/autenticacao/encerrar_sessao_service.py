class EncerrarSessaoService:
    """Logout: the session stops being valid immediately."""

    def executar(self, sessao):
        sessao.deletar()
