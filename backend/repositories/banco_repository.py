# Operações no banco como um todo (saúde e backup)
import sqlite3
from pathlib import Path
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from app.extensions import db

MIGRATIONS = Path(__file__).resolve().parents[1] / 'migrations'


# Consultas sobre o banco
class BancoRepository:
    # Confere se o banco responde e está na última migration
    @staticmethod
    def esquema_atualizado():
        db.session.execute(text('SELECT 1'))
        tabelas = inspect(db.engine).get_table_names()
        scripts = ScriptDirectory(str(MIGRATIONS))
        with db.engine.connect() as connection:
            atual = set(MigrationContext.configure(connection).get_current_heads())
        return set(db.metadata.tables).issubset(tabelas) and atual == set(scripts.get_heads())

    # Endereço do banco em uso
    @staticmethod
    def url():
        return db.engine.url

    # Copia o banco SQLite e confere a cópia
    @staticmethod
    def copiar_sqlite(origem, destino):
        source = sqlite3.connect(origem)
        target = sqlite3.connect(destino)
        try:
            with target:
                source.backup(target)
            return target.execute('PRAGMA integrity_check').fetchone()[0]
        finally:
            target.close()
            source.close()
