# Leitura do banco do protótipo antigo
import sqlite3


# Consultas no banco antigo
class LegadoRepository:
    # Lê as tabelas do protótipo
    @staticmethod
    def ler_prototipo(origem):
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
