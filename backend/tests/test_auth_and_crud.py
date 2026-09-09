import pytest
from sqlalchemy import select,text
from werkzeug.security import check_password_hash
from app import db
from app.models import Usuario,Dispositivo,AuthSession
from conftest import register,auth_headers


def test_registration_hash_login_and_revoked_logout(app,client):
    assert register(client).status_code==201
    token=client.get_cookie('edgehealth_session').value
    with app.app_context():
        user=db.session.scalar(select(Usuario))
        assert user.senha_hash!='senha-de-teste-123'
        assert check_password_hash(user.senha_hash,'senha-de-teste-123')
    assert client.get('/api/auth/me').json['empresa']['nome_fantasia']=='Empresa A'
    assert client.post('/api/auth/logout',json={},headers=auth_headers(client)).status_code==204
    client.set_cookie('edgehealth_session',token)
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':'admin@a.example','senha':'incorreta'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'admin@a.example','senha':'senha-de-teste-123'}).status_code==200


def test_protected_and_csrf(app,client,signed):
    assert app.test_client().get('/api/dispositivos').status_code==401
    assert signed.post('/api/dispositivos',json={}).status_code==403
    assert signed.get('/api/usuarios').status_code==200


def test_company_and_user_form_contract(signed,app):
    h=auth_headers(signed)
    assert signed.put('/api/empresa',json={'nome_fantasia':'Novo nome'},headers=h).json['nome_fantasia']=='Novo nome'
    response=signed.post('/api/usuarios',json={'nome':'Tecnico','email':'tecnico@a.example','senha':'outra-senha-123','papel':'TECNICO'},headers=h)
    assert response.status_code==201
    tech=app.test_client()
    assert tech.post('/api/auth/login',json={'email':'tecnico@a.example','senha':'outra-senha-123'}).status_code==200
    assert tech.get('/api/usuarios').status_code==403
    assert tech.get('/api/dispositivos').status_code==200
    assert signed.put('/api/usuarios/'+str(response.json['id']),json={'ativo':False},headers=h).status_code==200
    assert tech.get('/api/auth/me').status_code==401


def test_device_crud_and_operational_fields(signed,device,app):
    h=auth_headers(signed)
    id=device['id']
    assert device['status'] is None
    assert signed.get('/api/dispositivos').json[0]['id']==id
    assert signed.put(f'/api/dispositivos/{id}',json={'nome':'Novo','localizacao':'Andar 2'},headers=h).json['localizacao']=='Andar 2'
    for data in [{'ip':'x; whoami'},{'empresa_id':99},{'status':'ONLINE'}]:
        assert signed.put(f'/api/dispositivos/{id}',json=data,headers=h).status_code==400
    assert signed.post(f'/api/dispositivos/{id}/coletas',json={},headers=h).status_code==202
    assert signed.delete(f'/api/dispositivos/{id}',headers=h).status_code==204
    assert signed.get('/api/dispositivos').json==[]
    assert signed.get('/api/dispositivos?arquivados=1').json[0]['arquivado_em']
    with app.app_context(): assert db.session.get(Dispositivo,id) is not None

@pytest.mark.parametrize('field,value',[('cnpj','123'),('email','errado'),('senha','curta'),('nome','')])
def test_registration_invalid_input(client,field,value):
    data={'nome_fantasia':'Empresa','cnpj':'11222333000181','nome':'Nome','email':'a@b.example','senha':'senha-valida-123'}
    data[field]=value
    assert client.post('/api/auth/registro',json=data).status_code==400


def test_duplicate_cnpj_and_bad_payload(signed):
    assert register(signed,email='other@example.com').status_code==409
    assert signed.post('/api/dispositivos',json=[],headers=auth_headers(signed)).status_code==400
    assert signed.post('/api/dispositivos',json={'nome':'X','ip':'not-ip','tipo':'R','localizacao':'TI'},headers=auth_headers(signed)).status_code==400


def test_rate_limit(client):
    for _ in range(3): assert client.post('/api/auth/login',json={'email':'none@none.example','senha':'senhaerrada'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'none@none.example','senha':'senhaerrada'}).status_code==429


def test_fk_enforced(app):
    from sqlalchemy.exc import IntegrityError
    with app.app_context():
        assert db.session.execute(text('PRAGMA foreign_keys')).scalar()==1
        db.session.add(Usuario(empresa_id=999,nome='X',email='x@example.com',senha_hash='not-a-real-hash',papel='TECNICO'))
        with pytest.raises(IntegrityError): db.session.commit()
        db.session.rollback()
def test_password_whitespace_is_significant(client):
    from conftest import auth_headers
    secret = '  whitespace-matters  '
    registration = client.post('/api/auth/registro', json={
        'nome_fantasia': 'Empresa', 'cnpj': '11222333000181', 'nome': 'Admin',
        'email': 'whitespace@example.test', 'senha': secret})
    assert registration.status_code == 201
    assert client.post('/api/auth/logout', headers=auth_headers(client)).status_code == 204
    assert client.post('/api/auth/login', json={'email': 'whitespace@example.test', 'senha': secret.strip()}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'whitespace@example.test', 'senha': secret}).status_code == 200

def test_numeric_and_alphanumeric_cnpj(client):
    response = client.post('/api/auth/registro', json={
        'nome_fantasia': 'Empresa', 'cnpj': '12.abc.345/01de-35', 'nome': 'Admin',
        'email': 'cnpj@example.test', 'senha': 'cnpj-test-password'})
    assert response.status_code == 201
    assert response.json['empresa']['cnpj'] == '12ABC34501DE35'
    from conftest import auth_headers
    assert client.put('/api/empresa', json={'cnpj': '12ABC34501DE36'}, headers=auth_headers(client)).status_code == 400
    assert client.put('/api/empresa', json={'cnpj': '11.222.333/0001-81'}, headers=auth_headers(client)).status_code == 200
