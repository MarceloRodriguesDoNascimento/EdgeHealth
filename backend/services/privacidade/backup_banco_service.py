# Caso de uso: cópia de segurança do banco
import os
from repositories import BancoRepository


# Backup do banco
class BackupBancoService:
    # Copia o banco sem sobrescrever arquivo existente
    def executar(self, destino):
        url = BancoRepository.url()
        if url.get_backend_name() != 'sqlite' or not url.database:
            raise ValueError('O comando de backup suporta somente SQLite; use a ferramenta do banco utilizado.')
        if os.path.exists(destino):
            raise ValueError('O arquivo de destino já existe; escolha outro nome.')
        if BancoRepository.copiar_sqlite(url.database, destino) != 'ok':
            raise ValueError('A cópia não passou na verificação de integridade.')
