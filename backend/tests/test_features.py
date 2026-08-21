import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_empresa_crud_flow(client):
    r1 = client.post('/api/empresas', json={'nome_fantasia': 'Acme', 'cnpj': '12345678000199'})
    assert r1.status_code == 201
    empresa_id = r1.get_json()['id']

    r2 = client.get('/api/empresas')
    assert r2.status_code == 200
    assert any(item['id'] == empresa_id for item in r2.get_json())

    r3 = client.put(f'/api/empresas/{empresa_id}', json={'nome_fantasia': 'Acme Ltda'})
    assert r3.status_code == 200
    assert r3.get_json()['nome_fantasia'] == 'Acme Ltda'

    r4 = client.delete(f'/api/empresas/{empresa_id}')
    assert r4.status_code == 204


def test_dispositivo_ping_flow(client):
    empresa = client.post('/api/empresas', json={'nome_fantasia': 'Infra', 'cnpj': '12345678000100'})
    empresa_id = empresa.get_json()['id']

    r1 = client.post('/api/dispositivos', json={
        'nome': 'Router1',
        'ip': '10.0.0.1',
        'tipo': 'Roteador',
        'setor': 'Teste',
        'empresa_id': empresa_id,
    })
    assert r1.status_code == 201
    dispositivo_id = r1.get_json()['id']

    r2 = client.post(f'/api/dispositivos/{dispositivo_id}/ping', json={'status': 'online'})
    assert r2.status_code == 200
    assert r2.get_json()['status'] == 'online'
