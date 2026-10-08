"""Financial loss estimate: cost per hour, working hours, shared outages and the API around it."""
import csv
import io
import json
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import pytest
from flask_migrate import upgrade, check
from sqlalchemy import select, text
from app import create_app, db
from models import Diagnostico, Dispositivo, Empresa, Falha, Impacto, utcnow
from app.services import costs
from conftest import auth_headers, register

# 2026-10-07 is a Wednesday; São Paulo is UTC-3 all year (no DST since 2019). Working hours 08-18 local
# = 11:00-21:00 UTC.
WED = datetime(2026, 10, 7)
COSTS = {'salario_medio': '3000', 'total_funcionarios': 40, 'expediente': {'dias': [1, 2, 3, 4, 5], 'inicio': '08:00', 'fim': '18:00'}}


@pytest.fixture
def configured(signed):
    r = signed.put('/api/empresa/custos', json=COSTS, headers=auth_headers(signed))
    assert r.status_code == 200, r.json
    return signed


def make_failure(app, device_id, start, end=None, users=None, loss=None, direct=None, shared=False, tipo='INDISPONIBILIDADE'):
    with app.app_context():
        d = db.session.get(Dispositivo, device_id)
        if users is not None:
            d.usuarios_dependentes = users
        if loss is not None:
            d.perda_produtividade_pct = loss
        f = Falha(dispositivo_id=device_id, tipo=tipo, estado='ENCERRADA' if end else 'ABERTA', inicio=start, fim=end,
                  ultima_observacao=end or start, descricao='teste', encerramento='RECUPERACAO' if end else None)
        db.session.add(f)
        db.session.flush()
        db.session.add(Impacto(falha_id=f.id, custos_diretos=Decimal(direct) if direct is not None else None))
        if shared:
            db.session.add(Diagnostico(falha_id=f.id, descricao='x', estado='DISPONIVEL', causas=[{'regra': 'COMPARTILHADA'}]))
        db.session.commit()
        return f.id


def new_device(client, name, ip, tipo='Servidor', **extra):
    r = client.post('/api/dispositivos', json={'nome': name, 'ip': ip, 'tipo': tipo, 'localizacao': 'TI', **extra}, headers=auth_headers(client))
    assert r.status_code == 201, r.json
    return r.json


def estimate(app, failure_id, now=None):
    with app.app_context():
        return costs.full_estimate(db.session.get(Falha, failure_id), now=now)


def test_cost_per_hour_is_computed_from_salary_charges_and_hours(configured):
    c = configured.get('/api/empresa').json['custos']
    assert c['configurado'] and c['custo_hora'] == '23.18'  # 3000 × 1.7 ÷ 220 = 23.1818…
    assert c['fator_encargos'] == '1.7' and c['horas_mes'] == 220 and c['expediente']['dias'] == [1, 2, 3, 4, 5]
    assert c['assistente'] == 'CONCLUIDO'


def test_incident_entirely_inside_working_hours(app, configured, device):
    fid = make_failure(app, device['id'], WED.replace(hour=13), WED.replace(hour=15), users=25, loss=100, direct='250')
    e = estimate(app, fid)
    # 2 h × 25 × 23.1818… × 100% = 1159.09 (exact Decimal, rounded once) + 250
    assert e['valor'] == '1409.09' and e['em_andamento'] is False
    assert e['detalhe']['horas_expediente'] == '2.00' and e['detalhe']['custo_hora'] == '23.18'
    assert e['conta'] == '25 pessoas × R$ 23,18/h × 100% × 2,0 h de expediente + R$ 250,00 de custos diretos'
    assert e['aviso'] == costs.DISCLAIMER


def test_only_the_part_inside_working_hours_counts(app, configured, device):
    # 17:00 → 20:00 local: only 1 h before the end of the working day; the night adds nothing.
    fid = make_failure(app, device['id'], WED.replace(hour=20), WED.replace(hour=23), users=10, loss=50)
    assert estimate(app, fid)['detalhe']['horas_expediente'] == '1.00'
    # Wednesday 17:00 → Thursday 09:00 local = 1 h + 1 h.
    fid2 = make_failure(app, device['id'], WED.replace(hour=20) + timedelta(days=7), WED.replace(hour=12) + timedelta(days=8), users=10, loss=50)
    assert estimate(app, fid2)['detalhe']['horas_expediente'] == '2.00'


def test_weekend_costs_no_productivity_only_direct_costs(app, configured, device):
    saturday = WED + timedelta(days=3)
    fid = make_failure(app, device['id'], saturday.replace(hour=12), saturday.replace(hour=20), users=40, loss=100, direct='80')
    e = estimate(app, fid)
    assert e['detalhe']['horas_expediente'] == '0.00' and e['detalhe']['produtividade'] == '0.00'
    assert e['valor'] == '80.00'


def test_open_incident_is_a_partial_estimate_until_now(app, configured, device):
    fid = make_failure(app, device['id'], WED.replace(hour=12), users=4, loss=100)
    e = estimate(app, fid, now=WED.replace(hour=13, minute=30))
    assert e['em_andamento'] is True and e['detalhe']['horas_expediente'] == '1.50'
    assert e['valor'] == '139.09'  # 1.5 × 4 × 23.1818…
    assert e['detalhe']['calculado_ate'] == '2026-10-07T13:30:00Z'


def test_shared_outage_group_does_not_count_the_same_people_twice(app, configured, signed):
    devices = [new_device(signed, f'Andar {i}', f'10.0.0.{i}', 'Switch') for i in (1, 2, 3)]
    start, end = WED.replace(hour=13), WED.replace(hour=14)
    ids = [make_failure(app, d['id'], start + timedelta(seconds=i), end, users=u, loss=100, shared=True)
           for i, (d, u) in enumerate(zip(devices, (25, 10, 5)))]
    e = estimate(app, ids[1])
    g = e['grupo']
    assert sorted(g['falhas']) == sorted(ids) and g['pessoas_consideradas'] == 25 and g['pessoas_somadas'] == 40
    assert g['valor'] == '579.55'  # 1 h × 25 × 23.1818…, not 40 people
    assert 'não a soma' in g['explicacao']
    with app.app_context():
        company = db.session.get(Empresa, devices[0]['empresa_id'])
        total = costs.total_for(db.session.scalars(select(Falha)).all(), company)
    assert total['total'] == '579.55'  # sum of the individual estimates would be 927.27
    assert [t['nome'] for t in total['top_dispositivos']] == ['Andar 1', 'Andar 2', 'Andar 3']


def test_without_company_costs_nothing_is_invented(app, signed, device):
    fid = make_failure(app, device['id'], WED.replace(hour=13), WED.replace(hour=15), users=25, loss=100)
    e = estimate(app, fid)
    assert e == {'configurado': False, 'mensagem': costs.NOT_CONFIGURED}
    detail = signed.get(f'/api/falhas/{fid}').json
    assert detail['prejuizo']['configurado'] is False
    assert signed.get('/api/dashboard').json['custos']['configurado'] is False


@pytest.mark.parametrize('path,body', [
    ('/api/empresa/custos', {'salario_medio': '-1'}),
    ('/api/empresa/custos', {'salario_medio': 'abc'}),
    ('/api/empresa/custos', {'fator_encargos': '0.5'}),
    ('/api/empresa/custos', {'total_funcionarios': -3}),
    ('/api/empresa/custos', {'expediente': {'dias': [], 'inicio': '08:00', 'fim': '18:00'}}),
    ('/api/empresa/custos', {'expediente': {'dias': [1], 'inicio': '18:00', 'fim': '08:00'}}),
    ('/api/empresa/custos', {'fuso': 'Marte/Olimpo'}),
    ('/api/dispositivos/{id}', {'receita_hora_dependente': '-10'}),
    ('/api/dispositivos/{id}', {'perda_produtividade_pct': 101}),
    ('/api/dispositivos/{id}', {'usuarios_dependentes': -1}),
    ('/api/falhas/{fid}/impacto', {'custos_diretos': '-250'}),
])
def test_negative_and_invalid_values_are_refused(app, configured, device, path, body):
    fid = make_failure(app, device['id'], WED.replace(hour=13), WED.replace(hour=14))
    r = configured.put(path.format(id=device['id'], fid=fid), json=body, headers=auth_headers(configured))
    assert r.status_code == 400, r.json


def test_money_is_exact_decimal_from_number_or_text(app, configured, device):
    r = configured.put(f'/api/dispositivos/{device["id"]}', json={'receita_hora_dependente': '1234,565'}, headers=auth_headers(configured))
    assert r.json['receita_hora_dependente'] == '1234.57'
    r = configured.put('/api/empresa/custos', json={'salario_medio': 0.1}, headers=auth_headers(configured))
    assert r.json['custos']['salario_medio'] == '0.10'
    with app.app_context():
        raw = db.session.execute(text('SELECT salario_medio FROM empresas')).scalar()
    assert raw == '0.10'  # stored as exact text, never a float


def test_technician_sees_but_cannot_edit_company_costs(app, configured):
    configured.post('/api/usuarios', json={'nome': 'Tec', 'email': 'tec@a.example', 'senha': 'senha-tecnico-1'}, headers=auth_headers(configured))
    tech = app.test_client()
    tech.post('/api/auth/login', json={'email': 'tec@a.example', 'senha': 'senha-tecnico-1'})
    tech.post('/api/auth/aceite-termos', json={'aceite_termos': True}, headers=auth_headers(tech))
    assert tech.get('/api/empresa').json['custos']['custo_hora'] == '23.18'
    assert tech.put('/api/empresa/custos', json={'salario_medio': '1'}, headers=auth_headers(tech)).status_code == 403
    assert tech.post('/api/empresa/custos/pular', json={}, headers=auth_headers(tech)).status_code == 403


def test_other_company_cannot_see_or_change_the_estimate(app, configured, device):
    fid = make_failure(app, device['id'], WED.replace(hour=13), WED.replace(hour=15), users=25, loss=100)
    other = app.test_client()
    assert register(other, email='admin@b.example', cnpj='11444777000161', name='Empresa B').status_code == 201
    assert other.get(f'/api/falhas/{fid}').status_code == 404
    assert other.put(f'/api/falhas/{fid}/impacto', json={'custos_diretos': '1'}, headers=auth_headers(other)).status_code == 404
    assert other.put(f'/api/dispositivos/{device["id"]}', json={'usuarios_dependentes': 1}, headers=auth_headers(other)).status_code == 404
    assert other.get('/api/dashboard').json['custos']['configurado'] is False


@pytest.mark.parametrize('tipo,categoria,usuarios,perda', [
    ('Roteador principal', 'REDE', 40, 100), ('FIREWALL', 'REDE', 40, 100), ('Link de internet', 'REDE', 40, 100),
    ('Switch gerenciável', 'SWITCH', None, 100), ('Access Point', 'ACCESS_POINT', None, 50),
    ('Servidor de arquivos', 'SERVIDOR', 40, 50), ('Armazenamento (NAS)', 'SERVIDOR', 40, 50),
    ('Impressora', 'IMPRESSORA', 10, 30), ('Telefone VoIP', 'VOIP', 1, 100),
    ('Câmera IP', 'SEGURANCA', 0, 0), ('Sensor IoT', 'SEGURANCA', 0, 0),
    ('Máquina de cartão', 'PDV', 1, 100), ('PONTO DE VENDA', 'PDV', 1, 100),
    ('Geladeira inteligente', 'OUTROS', 1, 50), ('Serviço externo', 'OUTROS', 1, 50),
])
def test_defaults_by_device_type_ignore_case_and_accents(configured, tipo, categoria, usuarios, perda):
    d = configured.get('/api/dispositivos/impacto-padrao', query_string={'tipo': tipo}).json
    assert (d['categoria'], d['usuarios'], d['perda_pct']) == (categoria, usuarios, perda)
    assert d['sugerir_receita'] == (categoria == 'PDV')


def test_new_device_gets_type_defaults_and_explicit_values_win(configured):
    router = new_device(configured, 'R', '10.1.1.1', 'Roteador')
    assert (router['usuarios_dependentes'], router['perda_produtividade_pct']) == (40, 100)
    printer = new_device(configured, 'P', '10.1.1.2', 'Impressora', usuarios_dependentes=3, perda_produtividade_pct=10)
    assert (printer['usuarios_dependentes'], printer['perda_produtividade_pct']) == (3, 10)


def test_impact_users_override_the_device_and_direct_costs_are_saved(app, configured, device):
    fid = make_failure(app, device['id'], WED.replace(hour=13), WED.replace(hour=14), users=25, loss=100)
    r = configured.put(f'/api/falhas/{fid}/impacto', json={'usuarios_afetados': 5, 'custos_diretos': '99.90'}, headers=auth_headers(configured))
    assert r.status_code == 200 and r.json['impacto']['custos_diretos'] == '99.90'
    p = r.json['prejuizo']
    assert p['detalhe']['pessoas'] == 5 and p['detalhe']['origem_pessoas'] == 'informado na ocorrência'
    assert p['valor'] == '215.81'  # 1 h × 5 × 23.1818… + 99.90
    # Only direct costs: the people come from the device again (usuarios_afetados null).
    r = configured.put(f'/api/falhas/{fid}/impacto', json={'usuarios_afetados': None}, headers=auth_headers(configured))
    assert r.json['prejuizo']['detalhe']['pessoas'] == 25


def test_report_has_the_estimate_column_and_the_total(app, configured, device):
    make_failure(app, device['id'], WED.replace(hour=13), WED.replace(hour=15), users=25, loss=100, direct='250')
    r = configured.get('/api/relatorios/exportar', query_string={'inicio': '2026-10-01', 'fim': '2026-10-31'})
    z = zipfile.ZipFile(io.BytesIO(r.data))
    rows = list(csv.DictReader(io.StringIO(z.read('falhas.csv').decode('utf-8-sig')), delimiter=';'))
    assert rows[0]['prejuizo_estimado'] == '1409.09'
    assert json.loads(z.read('leia-me.json'))['prejuizo_estimado']['total'] == '1409.09'


def test_dashboard_shows_the_30_day_total_and_top_devices(app, configured, device):
    now = utcnow()
    start = now - timedelta(days=2)
    make_failure(app, device['id'], start, start + timedelta(days=1), users=25, loss=100)
    c = configured.get('/api/dashboard').json['custos']
    assert c['configurado'] and c['dias'] == 30 and Decimal(c['total']) > 0
    assert c['top_dispositivos'][0]['nome'] == device['nome']


def test_cost_assistant_can_be_skipped_once(configured, client):
    other = client  # same admin session: skipping after configuring keeps CONCLUIDO
    assert other.post('/api/empresa/custos/pular', json={}, headers=auth_headers(other)).json['custos']['assistente'] == 'CONCLUIDO'


def test_cost_assistant_skip_marks_it_as_skipped(signed):
    r = signed.post('/api/empresa/custos/pular', json={}, headers=auth_headers(signed))
    assert r.json['custos']['assistente'] == 'PULADO' and r.json['custos']['configurado'] is False


def test_upgrade_from_production_revision_keeps_data(tmp_path):
    """bc4dfbaec175 (deployed) -> head: rows survive, defaults apply, nothing is configured by itself."""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'prod.db')})
    migrations = str(Path(__file__).resolve().parents[1] / 'migrations')
    with app.app_context():
        upgrade(directory=migrations, revision='bc4dfbaec175')
        for sql in ("INSERT INTO empresas(id,nome_fantasia,cnpj,criada_em) VALUES (1,'A','11222333000181','2026-09-01')",
                    "INSERT INTO dispositivos(id,empresa_id,nome,ip,tipo,localizacao,falhas_consecutivas,sucessos_consecutivos,criado_em,proxima_coleta) "
                    "VALUES (1,1,'R','10.0.0.1','Roteador','TI',0,0,'2026-09-01','2026-09-01')",
                    "INSERT INTO falhas(id,dispositivo_id,tipo,estado,inicio,fim,ultima_observacao,descricao,severidade,justificativa,encerramento) "
                    "VALUES (1,1,'INDISPONIBILIDADE','ENCERRADA','2026-09-01 13:00:00','2026-09-01 14:00:00','2026-09-01 14:00:00','x','MEDIA','{}','RECUPERACAO')",
                    "INSERT INTO impactos(id,falha_id,usuarios_afetados,origem,atualizado_em) VALUES (1,1,7,'INFORMADO_PELO_USUARIO','2026-09-01')"):
            db.session.execute(text(sql))
        db.session.commit()
        upgrade(directory=migrations)
        check(directory=migrations)
        company = db.session.get(Empresa, 1)
        assert company.salario_medio is None and company.fator_encargos == Decimal('1.7') and company.horas_mes == 220
        assert (company.expediente_dias, company.expediente_inicio, company.expediente_fim, company.fuso) == ('12345', '08:00', '18:00', 'America/Sao_Paulo')
        assert db.session.get(Impacto, 1).usuarios_afetados == 7 and db.session.get(Impacto, 1).custos_diretos is None
        assert db.session.get(Dispositivo, 1).usuarios_dependentes is None
        assert costs.full_estimate(db.session.get(Falha, 1))['configurado'] is False
