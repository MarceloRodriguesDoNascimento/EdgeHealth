# Caso de uso: logout
# Encerra a sessão
class EncerrarSessaoService:
    # Apaga a sessão do banco
    def executar(self, sessao):
        sessao.deletar()
