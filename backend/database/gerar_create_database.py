"""Regenerates backend/database/create_database.sql from the Alembic migrations.

The migrations are applied to an empty temporary SQLite database and the final schema stored by
SQLite (sqlite_master) is written in dependency order, one column/constraint per line. Definitions
are copied verbatim, so the script creates exactly the schema of "flask db upgrade".

Usage (inside backend/, with the virtualenv active):
    python database/gerar_create_database.py
"""
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DESTINO = BACKEND / 'database' / 'create_database.sql'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Parents before children (foreign keys); alembic_version last.
ORDEM = ['empresas', 'usuarios', 'auth_sessions', 'login_attempts', 'coletores', 'dispositivos', 'metricas',
         'falhas', 'impactos', 'diagnosticos', 'recomendacoes', 'diagnostico_recomendacoes', 'registros_legados',
         'alembic_version']

CABECALHO = """\
-- =====================================================================================
-- EdgeHealth: criação do banco de dados SQLite e de todas as tabelas
-- =====================================================================================
-- Arquivo GERADO a partir das migrations Alembic (backend/migrations/versions); não edite
-- à mão. Para regenerar depois de criar uma migration:
--     cd backend && python database/gerar_create_database.py
-- (tests/test_database_script.py falha se este script ficar diferente das migrations.)
--
-- Uso, em um arquivo de banco NOVO e vazio:
--     cd backend
--     sqlite3 instance/edgehealth.db < database/create_database.sql
--
-- O banco criado já registra a revisão atual em alembic_version, então
-- "flask db upgrade" o reconhece e aplicará somente migrations futuras.
-- Tipos: SQLite usa afinidade de tipo; VARCHAR(n) documenta o limite validado pela
-- aplicação. Valores monetários são texto decimal exato (ex.: '3000.00'), nunca float.
-- Datas são UTC no formato 'AAAA-MM-DD HH:MM:SS.ffffff'.
-- =====================================================================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;
"""


def dividir(corpo):
    """Splits the body of a CREATE TABLE on top-level commas (outside parentheses and quotes)."""
    partes, atual, nivel, aspas = [], '', 0, None
    for ch in corpo:
        if aspas:
            aspas = None if ch == aspas else aspas
        elif ch in ('"', "'"):
            aspas = ch
        elif ch == '(':
            nivel += 1
        elif ch == ')':
            nivel -= 1
        elif ch == ',' and nivel == 0:
            partes.append(atual.strip())
            atual = ''
            continue
        atual += ch
    partes.append(atual.strip())
    return [re.sub(r'\s+', ' ', p) for p in partes if p]


def formatar_tabela(sql):
    inicio, fim = sql.index('('), sql.rindex(')')
    cabecalho = re.sub(r'\s+', ' ', sql[:inicio]).strip()
    itens = dividir(sql[inicio + 1:fim])
    return cabecalho + ' (\n    ' + ',\n    '.join(itens) + '\n);'


def esquema_das_migrations():
    from flask_migrate import upgrade
    from app import create_app, db
    with tempfile.TemporaryDirectory() as pasta:
        arquivo = Path(pasta) / 'schema.db'
        app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + arquivo.as_posix()})
        with app.app_context():
            upgrade(directory=str(BACKEND / 'migrations'))
            db.engine.dispose()
        conexao = sqlite3.connect(arquivo)
        try:
            objetos = conexao.execute("SELECT type, name, tbl_name, sql FROM sqlite_master "
                                      "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            revisao = conexao.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        finally:
            conexao.close()
    return objetos, revisao


def gerar():
    from services.diagnosticos.popular_catalogo_service import PopularCatalogoService
    objetos, revisao = esquema_das_migrations()
    tabelas = {nome: sql for tipo, nome, _, sql in objetos if tipo == 'table'}
    assert set(tabelas) == set(ORDEM), f'Atualize ORDEM com as tabelas: {sorted(set(tabelas) ^ set(ORDEM))}'
    linhas = [CABECALHO]
    for tabela in ORDEM:
        linhas.append(f'-- {tabela}')
        linhas.append(formatar_tabela(tabelas[tabela]))
        for tipo, nome, alvo, sql in objetos:
            if tipo == 'index' and alvo == tabela:
                linhas.append(re.sub(r'\s+', ' ', sql).strip() + ';')
        linhas.append('')
    linhas.append('-- Revisão Alembic deste esquema: "flask db upgrade" parte daqui.')
    linhas.append(f"INSERT INTO alembic_version (version_num) VALUES ('{revisao}');")
    linhas.append('')
    linhas.append('-- =====================================================================================')
    linhas.append('-- Dados iniciais: catálogo de ações corretivas (o mesmo de PopularCatalogoService e do')
    linhas.append('-- comando "flask seed-catalog"). São recomendações, não medições de rede.')
    linhas.append('-- =====================================================================================')
    for regra, codigo, titulo, acao in PopularCatalogoService.CATALOGO:
        valores = ', '.join("'" + v.replace("'", "''") + "'" for v in (regra, codigo, titulo, acao))
        linhas.append(f'INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ({valores});')
    linhas.append('')
    linhas.append('COMMIT;')
    return '\n'.join(linhas) + '\n'


if __name__ == '__main__':
    DESTINO.write_text(gerar(), encoding='utf-8', newline='\n')
    print(f'{DESTINO.relative_to(BACKEND)} gerado.')
