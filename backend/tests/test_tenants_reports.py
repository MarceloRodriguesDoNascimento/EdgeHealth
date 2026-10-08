import csv
import io
import zipfile
from sqlalchemy import select
from app import db
from models import Dispositivo,Falha,Diagnostico,utcnow
from app.services.monitoring import record_result,ProbeResult
from conftest import register,auth_headers


def test_cross_tenant_isolation_all_resources(app,signed,device):
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        metric=record_result(d,ProbeResult(4,3,250))
        db.session.commit()
        mid=metric.id
        fid=db.session.scalar(select(Falha.id))
        did=db.session.scalar(select(Diagnostico.id))
    other=app.test_client()
    assert register(other,'admin@b.example','11444777000161','Empresa B').status_code==201
    paths=[f"/api/dispositivos/{device['id']}",f'/api/metricas/{mid}',f'/api/falhas/{fid}',f'/api/diagnosticos/{did}',
           f"/api/metricas?dispositivo_id={device['id']}",f"/api/dashboard?dispositivo_id={device['id']}",f"/api/relatorios/exportar?dispositivo_id={device['id']}"]
    for path in paths: assert other.get(path).status_code==404,path
    assert other.put(f"/api/dispositivos/{device['id']}",json={'nome':'invasao'},headers=auth_headers(other)).status_code==404
    assert other.delete(f"/api/dispositivos/{device['id']}",headers=auth_headers(other)).status_code==404
    assert other.put(f'/api/falhas/{fid}/impacto',json={'usuarios_afetados':99},headers=auth_headers(other)).status_code==404
    assert other.post('/api/metricas',json={'dispositivo_id':device['id'],'valor':1},headers=auth_headers(other)).status_code in (404,405)
    assert other.get('/api/dispositivos').json==[]
    assert other.get('/api/metricas').json['total']==0
    assert other.get('/api/falhas').json['total']==0
    assert other.get('/api/dashboard').json['indicadores']['total']==0
    archive=zipfile.ZipFile(io.BytesIO(other.get('/api/relatorios/exportar').data))
    assert len(list(csv.reader(io.StringIO(archive.read('metricas.csv').decode('utf-8-sig')),delimiter=';')))==1


def test_dashboard_history_export_and_recommendations(app,signed,device):
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        record_result(d,ProbeResult(4,3,210))
        db.session.commit()
    dash=signed.get('/api/dashboard').json
    assert dash['indicadores']['total']==1 and dash['indicadores']['instaveis']==1
    assert dash['indicadores']['falhas_abertas']==1 and len(dash['serie'])==1
    assert sum(dash['severidades'].values())==1
    failure=signed.get('/api/falhas?estado=ABERTA').json['items'][0]
    detail=signed.get('/api/falhas/'+str(failure['id'])).json
    assert detail['diagnostico']['recomendacoes']
    assert detail['diagnostico']['causas'][0]['regra']=='CONGESTIONAMENTO'
    assert detail['duracao_segundos']>=0
    res=signed.get('/api/relatorios/exportar')
    assert res.status_code==200 and res.mimetype=='application/zip'
    z=zipfile.ZipFile(io.BytesIO(res.data))
    for name in ['dispositivos','metricas','falhas','diagnosticos']:
        rows=list(csv.DictReader(io.StringIO(z.read(name+'.csv').decode('utf-8-sig')),delimiter=';'))
        assert len(rows)==1,name
    assert signed.get('/api/metricas?tipo=latencia').json['items'][0]['latencia_ms']==210
    assert signed.get('/api/metricas?inicio=2030-01-01&fim=2020-01-01').status_code==400
    assert signed.get('/api/metricas?tipo=inventado').status_code==400


def test_company_payload_cannot_select_tenant(signed):
    assert signed.post('/api/usuarios',json={'nome':'X','email':'x@y.com','senha':'longpassword','empresa_id':900},headers=auth_headers(signed)).status_code==400
