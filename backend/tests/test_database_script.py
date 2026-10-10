"""database/create_database.sql must create exactly the schema of the Alembic migrations."""
import re
import sqlite3
from pathlib import Path
import pytest
from alembic.script import ScriptDirectory
from flask_migrate import check, upgrade
from app import create_app, db

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND / 'database' / 'create_database.sql'
MIGRATIONS = str(BACKEND / 'migrations')


def app_for(path):
    return create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + path.as_posix()})


@pytest.fixture
def databases(tmp_path):
    by_script = tmp_path / 'script.db'
    connection = sqlite3.connect(by_script)
    connection.executescript(SCRIPT.read_text(encoding='utf-8'))
    connection.close()
    by_migrations = tmp_path / 'migrations.db'
    app = app_for(by_migrations)
    with app.app_context():
        upgrade(directory=MIGRATIONS)
        db.engine.dispose()
    return by_script, by_migrations


def normalized(sql):
    sql = re.sub(r'\s+', ' ', sql)
    return re.sub(r' ?([(),]) ?', r'\1', sql).strip()


def describe(path):
    """Everything SQLite knows about the schema, per table."""
    c = sqlite3.connect(path)
    try:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        schema = {}
        for t in tables:
            sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()[0]
            indexes = {}
            for _, name, unique, origin, partial in c.execute(f'PRAGMA index_list("{t}")'):
                columns = [r[2] for r in c.execute(f'PRAGMA index_info("{name}")')]
                index_sql = c.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
                where = re.sub(r'\s+', ' ', index_sql[0].split(' WHERE ', 1)[1]) if index_sql and index_sql[0] and ' WHERE ' in index_sql[0] else None
                key = name if not name.startswith('sqlite_autoindex') else ('auto', tuple(columns))
                indexes[key] = (unique, origin, partial, tuple(columns), where)
            schema[t] = dict(
                columns=[(r[1], r[2], r[3], r[4], r[5]) for r in c.execute(f'PRAGMA table_info("{t}")')],
                foreign_keys=sorted((r[2], r[3], r[4], r[5], r[6]) for r in c.execute(f'PRAGMA foreign_key_list("{t}")')),
                indexes=indexes,
                # CHECK, UNIQUE and constraint names only exist in the CREATE TABLE text.
                definition=normalized(sql),
            )
        return schema
    finally:
        c.close()


def test_script_creates_the_same_schema_as_the_migrations(databases):
    by_script, by_migrations = databases
    script, migrations = describe(by_script), describe(by_migrations)
    assert sorted(script) == sorted(migrations)
    for table in migrations:
        for aspect in ('columns', 'foreign_keys', 'indexes', 'definition'):
            assert script[table][aspect] == migrations[table][aspect], f'{table}.{aspect} difere das migrations'
    # The comparison is not vacuous: 14 tables with their CHECK/UNIQUE/FK constraints and partial indexes.
    assert len(migrations) == 14
    assert sum(t['definition'].count('CONSTRAINT') for t in migrations.values()) >= 40
    assert migrations['falhas']['indexes']['uq_falha_aberta_dispositivo'][4] == "estado = 'ABERTA'"


def test_script_is_at_the_latest_migration_and_passes_db_check(databases):
    by_script, _ = databases
    heads = ScriptDirectory(MIGRATIONS).get_heads()
    with sqlite3.connect(by_script) as c:
        assert [r[0] for r in c.execute('SELECT version_num FROM alembic_version')] == heads, \
            'Nova migration: regenere database/create_database.sql (python database/gerar_create_database.py)'
    app = app_for(by_script)
    with app.app_context():
        check(directory=MIGRATIONS)  # raises if the models differ from the database
        upgrade(directory=MIGRATIONS)  # recognized as up to date: nothing to apply
        db.engine.dispose()


def test_script_loads_the_recommendation_catalog(databases):
    from services.diagnosticos.popular_catalogo_service import PopularCatalogoService
    by_script, _ = databases
    with sqlite3.connect(by_script) as c:
        rows = c.execute('SELECT regra, codigo, titulo, acao FROM recomendacoes ORDER BY id').fetchall()
        assert c.execute('PRAGMA foreign_key_check').fetchall() == []
    assert len(rows) == 8 and rows == [tuple(item) for item in PopularCatalogoService.CATALOGO]
