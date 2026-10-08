import sqlite3


class LegadoRepository:
    """Read-only access to the prototype SQLite database being imported."""

    @staticmethod
    def ler_prototipo(origem):
        """{table: [rows as dict]} of every user table, read in one read-only transaction."""
        connection = sqlite3.connect(origem.as_uri() + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
            names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            if 'alembic_version' in names or not {'empresas', 'usuarios', 'dispositivos'} <= set(names):
                raise ValueError('A origem não é um banco do protótipo EdgeHealth reconhecido.')
            return {name: [dict(r) for r in connection.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}
        finally:
            connection.close()
