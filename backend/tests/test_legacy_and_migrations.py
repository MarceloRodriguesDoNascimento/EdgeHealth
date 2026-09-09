import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from flask_migrate import upgrade, check
from sqlalchemy import select, func, text

from app import create_app, db
from app.models import Empresa, Usuario, Dispositivo, Metrica, Falha, RegistroLegado, Recomendacao
from app.services.legacy import import_legacy


def test_fresh_migrations_and_model_consistency(tmp_path):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'fresh.db')})
    migrations = str(Path(__file__).resolve().parents[1] / 'migrations')
    with app.app_context():
        upgrade(directory=migrations)
        upgrade(directory=migrations)  # A second deployment is idempotent.
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
