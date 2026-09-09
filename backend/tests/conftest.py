import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app, db
from app.services.catalog import seed_catalog

@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(tmp_path/'test.db'),'LOGIN_MAX_ATTEMPTS':3})
    with app.app_context():
        db.create_all()
        seed_catalog()
        db.session.commit()
    yield app
    with app.app_context(): db.engine.dispose()

@pytest.fixture
def client(app): return app.test_client()

def register(client,email='admin@a.example',cnpj='11222333000181',name='Empresa A'):
    return client.post('/api/auth/registro',json={'nome_fantasia':name,'cnpj':cnpj,'nome':'Administrador','email':email,'senha':'senha-de-teste-123'})

def auth_headers(client):
    cookie=client.get_cookie('edgehealth_csrf')
    return {'X-CSRF-Token':cookie.value} if cookie else {}

@pytest.fixture
def signed(client):
    assert register(client).status_code==201
    return client

@pytest.fixture
def device(signed):
    response=signed.post('/api/dispositivos',json={'nome':'Roteador','ip':'127.0.0.1','tipo':'Servidor','localizacao':'Sala TI'},headers=auth_headers(signed))
    assert response.status_code==201,response.json
    return response.json
