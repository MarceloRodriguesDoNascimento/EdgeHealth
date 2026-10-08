import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from flask_migrate import upgrade, downgrade, check
from sqlalchemy import select, func, text

from app import create_app, db
from models import Empresa, Usuario, Dispositivo, Metrica, Falha, RegistroLegado, Recomendacao
from app.services.legacy import import_legacy


def test_fresh_migrations_and_model_consistency(tmp_path):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'fresh.db')})
    migrations = str(Path(__file__).resolve().parents[1] / 'migrations')
    with app.app_context():
        upgrade(directory=migrations)
        upgrade(directory=migrations)  # A second deployment is idempotent.
        check(directory=migrations)
        downgrade(directory=migrations, revision='7c7ba005affc')  # Empty database: reversible.
        upgrade(directory=migrations)
        check(directory=migrations)
        assert db.session.execute(text('PRAGMA foreign_keys')).scalar() == 1
        assert db.session.execute(text('PRAGMA foreign_key_check')).all() == []
        assert db.session.scalar(select(func.count()).select_from(Empresa)) == 0
    runner = app.test_cli_runner()
    assert runner.invoke(args=['seed-catalog']).exit_code == 0
    assert runner.invoke(args=['seed-catalog']).exit_code == 0
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Recomendacao)) == 8
    assert app.test_client().get('/api/health').status_code == 200


def test_upgrade_from_previous_release_preserves_history(tmp_path):
    """A database at 7c7ba005affc (first published MVP) upgrades in place without losing rows."""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'old.db')})
    migrations = str(Path(__file__).resolve().parents[1] / 'migrations')
    with app.app_context():
        upgrade(directory=migrations, revision='7c7ba005affc')
        db.session.execute(text("INSERT INTO empresas(id,nome_fantasia,cnpj,criada_em) VALUES (1,'A','11222333000181','2026-09-01')"))
        db.session.execute(text("INSERT INTO usuarios(id,empresa_id,nome,email,senha_hash,papel,ativo,criada_em) VALUES (1,1,'Adm','a@a.example','x','ADMIN',1,'2026-09-01')"))
        db.session.execute(text("INSERT INTO dispositivos(id,empresa_id,nome,ip,tipo,localizacao,status,falhas_consecutivas,sucessos_consecutivos,criado_em,proxima_coleta) "
                                "VALUES (1,1,'R','10.0.0.1','Roteador','TI','OFFLINE',3,0,'2026-09-01','2026-09-01')"))
        db.session.execute(text("INSERT INTO metricas(id,dispositivo_id,coletada_em,respondeu,pacotes_enviados,pacotes_recebidos,perda_pacotes_pct,status) "
                                "VALUES (1,1,'2026-09-01 10:00:00',0,4,0,100,'OFFLINE')"))
        db.session.execute(text("INSERT INTO falhas(id,dispositivo_id,tipo,estado,inicio,ultima_observacao,descricao,severidade,justificativa) "
                                "VALUES (1,1,'INDISPONIBILIDADE','ABERTA','2026-09-01 10:00:00','2026-09-01 10:00:00','x','MEDIA','{}')"))
        db.session.commit()
        upgrade(directory=migrations)
        check(directory=migrations)
        assert db.session.execute(text('PRAGMA foreign_key_check')).all() == []
        metric = db.session.get(Metrica, 1)
        assert metric.coletor_id is None and metric.fora_de_ordem is False and metric.status == 'OFFLINE'
        assert db.session.get(Dispositivo, 1).coletor_id is None
        assert db.session.get(Falha, 1).estado == 'ABERTA'
        assert db.session.get(Usuario, 1).termos_versao is None  # must accept the terms at next login


def test_legacy_preserved_without_fabricated_measurements_or_plaintext_passwords(app, tmp_path):
    source = tmp_path / 'prototype.db'
    with sqlite3.connect(source) as old:
        old.executescript('''
            CREATE TABLE empresas(id INTEGER PRIMARY KEY,nome_fantasia TEXT,cnpj TEXT);
            CREATE TABLE usuarios(id INTEGER PRIMARY KEY,empresa_id INTEGER,nome TEXT,email TEXT,senha TEXT);
            CREATE TABLE dispositivos(id INTEGER PRIMARY KEY,empresa_id INTEGER,nome TEXT,ip TEXT,tipo TEXT,setor TEXT,status TEXT,latencia REAL);
            CREATE TABLE metricas(id INTEGER PRIMARY KEY,dispositivo_id INTEGER,latencia REAL);
        ''')
        old.execute('INSERT INTO empresas VALUES (1,?,?)', ('Empresa legada', '11222333000181'))
        old.execute('INSERT INTO usuarios VALUES (1,1,?,?,?)', ('Operador', 'operator@legacy.example', 'old-insecure-password'))
        old.execute('INSERT INTO dispositivos VALUES (1,1,?,?,?,?,?,12.5)', ('Servidor', '127.0.0.1', 'Servidor', 'Sala TI', 'online'))
        old.execute('INSERT INTO dispositivos VALUES (2,NULL,?,?,?,?,?,12.5)', ('Sem empresa', '127.0.0.2', 'Servidor', 'Sala TI', 'online'))
        old.execute('INSERT INTO metricas VALUES (1,1,12.5)')
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    with app.app_context():
        report = import_legacy(source)
        assert report['empresas'] == report['usuarios'] == report['dispositivos'] == 1
        assert report['registros_preservados'] == 5 and report['quarentena'] == 2
        d = db.session.scalar(select(Dispositivo))
        assert d.status is None and d.ultima_coleta is None and d.latencia_ms is None
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 0
        assert db.session.scalar(select(func.count()).select_from(Falha)) == 0
        user = db.session.scalar(select(Usuario))
        assert not user.ativo and user.papel == 'TECNICO'
        assert user.senha_hash.startswith('scrypt:')
        record = db.session.scalar(select(RegistroLegado).where(RegistroLegado.tabela == 'usuarios'))
        assert 'old-insecure-password' not in json.dumps(record.dados)
        metric = db.session.scalar(select(RegistroLegado).where(RegistroLegado.tabela == 'metricas'))
        assert metric.dados['latencia'] == 12.5 and metric.resultado == 'QUARENTENA'
        with pytest.raises(ValueError, match='vazio'):
            import_legacy(source)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    runner = app.test_cli_runner()
    activation = runner.invoke(args=['activate-user', '--email', 'operator@legacy.example', '--admin'], input='new-secure-password\nnew-secure-password\n')
    assert activation.exit_code == 0, activation.output
    login = app.test_client().post('/api/auth/login', json={'email': 'operator@legacy.example', 'senha': 'new-secure-password'})
    assert login.status_code == 200 and login.json['usuario']['papel'] == 'ADMIN'
    output = tmp_path / 'review.jsonl'
    assert runner.invoke(args=['export-legacy', '--output', str(output)]).exit_code == 0
    assert len(output.read_text().splitlines()) == 5
    assert runner.invoke(args=['export-legacy', '--output', str(output)]).exit_code != 0
