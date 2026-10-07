import json
import sqlite3
from datetime import timedelta
from sqlalchemy import select, func
from app import create_app, db
from app.models import Dispositivo, Metrica, Empresa, Usuario, Falha, utcnow
from app.services.monitoring import ProbeResult, record_result
from conftest import auth_headers


def test_retention_purges_old_samples_but_keeps_incidents(app, device):
    with app.app_context():
        d = db.session.get(Dispositivo, device['id'])
        record_result(d, ProbeResult(4, 3, 300), utcnow() - timedelta(days=200))
        record_result(d, ProbeResult(4, 4, 1), utcnow() - timedelta(days=1))
        db.session.commit()
    runner = app.test_cli_runner()
    preview = runner.invoke(args=['purge-history', '--dry-run'])
    assert preview.exit_code == 0 and json.loads(preview.output)['metricas'] == 1
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 2
    assert runner.invoke(args=['purge-history', '--days', '10']).exit_code != 0  # below the safety floor
    assert json.loads(runner.invoke(args=['purge-history']).output)['metricas'] == 1
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica)) == 1
        failure = db.session.scalar(select(Falha))
        assert failure is not None  # incident history is not part of the raw-sample retention


def test_anonymization_keeps_company_history(app, signed):
    h = auth_headers(signed)
    signed.post('/api/usuarios', json={'nome': 'Maria Técnica', 'email': 'maria@a.example', 'senha': 'senha-tecnica-1'}, headers=h)
    runner = app.test_cli_runner()
    assert runner.invoke(args=['anonymize-user', '--email', 'maria@a.example']).exit_code != 0  # requires --yes
    assert runner.invoke(args=['anonymize-user', '--email', 'admin@a.example', '--yes']).exit_code != 0  # sole admin
    assert runner.invoke(args=['anonymize-user', '--email', 'maria@a.example', '--yes']).exit_code == 0
    with app.app_context():
        user = db.session.scalar(select(Usuario).where(Usuario.anonimizado_em.isnot(None)))
        assert user.nome == 'Usuário anonimizado' and 'maria' not in user.email and not user.ativo
    assert app.test_client().post('/api/auth/login', json={'email': 'maria@a.example', 'senha': 'senha-tecnica-1'}).status_code == 401


def test_backup_is_consistent_and_never_overwrites(app, signed, tmp_path):
    output = tmp_path / 'backup.db'
    runner = app.test_cli_runner()
    assert runner.invoke(args=['backup', '--output', str(output)]).exit_code == 0
    with sqlite3.connect(output) as copy:
        assert copy.execute('SELECT count(*) FROM empresas').fetchone()[0] == 1
    assert runner.invoke(args=['backup', '--output', str(output)]).exit_code != 0


def test_proxy_and_secure_cookie_configuration(tmp_path):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'p.db'),
                      'SESSION_COOKIE_SECURE': True, 'TRUST_PROXY': 1})
    with app.app_context():
        db.create_all()
    client = app.test_client()
    response = client.post('/api/auth/registro', json={'nome_fantasia': 'E', 'cnpj': '11222333000181', 'nome': 'A',
                                                       'email': 'a@e.example', 'senha': 'senha-de-teste-123', 'aceite_termos': True},
                           headers={'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '203.0.113.9'})
    assert response.status_code == 201
    cookies = response.headers.getlist('Set-Cookie')
    assert all('Secure' in c and 'SameSite=Lax' in c for c in cookies)
    assert any('HttpOnly' in c and c.startswith('edgehealth_session=') for c in cookies)
    assert response.headers['Strict-Transport-Security']
