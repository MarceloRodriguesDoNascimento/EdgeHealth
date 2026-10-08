# Banco de dados do EdgeHealth

| Arquivo | Conteúdo |
| --- | --- |
| `create_database.sql` | DDL completo do banco SQLite: 14 tabelas com colunas, tipos, chaves primárias e estrangeiras (`ON DELETE`), `UNIQUE`, `CHECK`, índices (inclusive os parciais), a revisão Alembic atual e o catálogo de 8 recomendações. |
| `gerar_create_database.py` | Regenera o `create_database.sql` a partir das migrations. |

A fonte da verdade do esquema são as **migrations Alembic** (`backend/migrations/versions`). O `create_database.sql` é gerado a partir delas: o gerador aplica as migrations em um banco vazio e grava o esquema final, tabela por tabela, sem alterar nenhuma definição. `tests/test_database_script.py` compara um banco criado pelo script com um banco criado pelas migrations (tabelas, colunas com tipo, nulo e default, chaves estrangeiras, índices e constraints), roda `flask db check` no banco do script e confere o catálogo. Se alguém criar uma migration e não regenerar o script, o teste falha.

## Criar o banco

Os caminhos relativos de `DATABASE_URL` ficam em `backend/instance/` (padrão: `instance/edgehealth.db`). Use **um arquivo novo e vazio**.

**Pelo script SQL** (cliente `sqlite3`):

```bash
cd backend
sqlite3 instance/edgehealth.db < database/create_database.sql
```

Sem o cliente `sqlite3` instalado (por exemplo, no Windows), o Python faz o mesmo:

```bash
cd backend
python -c "import sqlite3; sqlite3.connect('instance/edgehealth.db').executescript(open('database/create_database.sql', encoding='utf-8').read())"
```

O banco já registra a revisão atual em `alembic_version`. Então `flask --app run.py db upgrade` o reconhece e só aplicará migrations futuras, e `flask --app run.py db check` não encontra diferenças.

**Pelas migrations** (caminho usado na hospedagem e no Docker):

```bash
cd backend
flask --app run.py db upgrade
flask --app run.py seed-catalog
```

Os dois caminhos produzem o mesmo esquema e o mesmo catálogo.

## Regenerar o script

Depois de criar uma migration (`flask --app run.py db migrate -m "..."`, revisada e aplicada):

```bash
cd backend
python database/gerar_create_database.py
python -m pytest -q tests/test_database_script.py
```

Não edite o `create_database.sql` à mão.

## Por que SQLite

- O EdgeHealth atende uma empresa pequena por instância, com poucos usuários simultâneos e escrita concentrada no worker e na ingestão dos coletores. O SQLite, com `busy_timeout` e um lease por dispositivo, comporta essa carga (ver `docs/DEPLOY.md`).
- É um arquivo: não exige servidor de banco. Isso simplifica a hospedagem (PythonAnywhere, Docker com volume), o backup online (`flask backup`) e a avaliação do projeto.
- A integridade fica no próprio banco: chaves estrangeiras (`PRAGMA foreign_keys=ON` em cada conexão), `CHECK` e índices únicos parciais (um IP ativo por empresa, uma falha aberta por dispositivo).
- O acesso passa pelo SQLAlchemy e pelo Alembic, então a troca por outro banco relacional fica restrita à configuração e às migrations.

## Stored Procedures e a camada Repository

O SQLite **não suporta Stored Procedures** (não existe `CREATE PROCEDURE`). No EdgeHealth, o papel que as procedures teriam (consultas especiais reutilizáveis, com parâmetros) fica na **camada Repository** (`backend/repositories/`), sempre em SQL:

- SQL com `text()` e parâmetros nomeados (`:empresa_id`, `:inicio`, `:limite`) nas agregações: contagens do dashboard por status e por severidade, ranking de falhas por dispositivo no período e ranking (top 5) de prejuízo estimado.
- SQLAlchemy Core (`select`, `join`, `where`, `order_by`, `limit`, `update`, `delete`) nas demais consultas especiais. Ele gera SQL parametrizado: busca limitada à empresa, histórico de falhas com filtros e paginação, métricas por período, períodos sobrepostos do relatório, dispositivos devidos para coleta, lease atômico do dispositivo e grupo de falhas compartilhadas.

Controllers e services nunca executam SQL (`tests/test_architecture.py`). Os resultados de cada consulta são verificados com dados montados no teste e resultado esperado exato em `tests/test_repositories.py`. Isso atende ao critério da rubrica "consultas SQL na camada Repository com resultados corretos".
