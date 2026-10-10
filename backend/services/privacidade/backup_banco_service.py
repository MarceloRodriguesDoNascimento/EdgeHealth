import os
from repositories import BancoRepository


class BackupBancoService:
    """Consistent online copy of the SQLite database (never overwrites a file)."""

    def executar(self, destino):
        url = BancoRepository.url()
        if url.get_backend_name() != 'sqlite' or not url.database:
            raise ValueError('O comando de backup suporta somente SQLite; use a ferramenta do banco utilizado.')
        if os.path.exists(destino):
            raise ValueError('O arquivo de destino já existe; escolha outro nome.')
        if BancoRepository.copiar_sqlite(url.database, destino) != 'ok':
            raise ValueError('A cópia não passou na verificação de integridade.')
