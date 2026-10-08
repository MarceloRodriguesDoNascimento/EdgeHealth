import sqlite3
from pathlib import Path
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from app.extensions import db

MIGRATIONS = Path(__file__).resolve().parents[1] / 'migrations'


class BancoRepository:
    """Database-level operations: readiness check, location and online SQLite backup."""

    @staticmethod
    def esquema_atualizado():
        """True when the database answers, every table exists and it is at the migration head."""
        db.session.execute(text('SELECT 1'))
        tabelas = inspect(db.engine).get_table_names()
        scripts = ScriptDirectory(str(MIGRATIONS))
        with db.engine.connect() as connection:
            atual = set(MigrationContext.configure(connection).get_current_heads())
        return set(db.metadata.tables).issubset(tabelas) and atual == set(scripts.get_heads())

    @staticmethod
    def url():
        return db.engine.url

    @staticmethod
    def copiar_sqlite(origem, destino):
        """Online copy with sqlite3's backup API; returns the destination integrity_check result."""
        source = sqlite3.connect(origem)
        target = sqlite3.connect(destino)
        try:
            with target:
                source.backup(target)
            return target.execute('PRAGMA integrity_check').fetchone()[0]
        finally:
            target.close()
            source.close()
