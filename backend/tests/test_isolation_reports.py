import io,json,zipfile
from datetime import timedelta
from sqlalchemy import select
from app import db
from models import Dispositivo,Falha,Diagnostico,Metrica,utcnow
from services.monitoramento import ProbeResult, RegistrarMedicaoService
from conftest import register,auth_headers

def test_every_tenant_boundary_and_csv_content(app,signed,device):
    other=app.test_client()
    response=register(other,'b@b.example','11444777000161','Empresa B')
    assert response.status_code==201,response.json
    d=other.post('/api/dispositivos',json={'nome':'SIGILO-B','ip':'127.0.0.2','tipo':'PC','localizacao':'B'},headers=auth_headers(other)).json
    with app.app_context():
        da=db.session.get(Dispositivo,device['id'])
        dbb=db.session.get(Dispositivo,d['id'])
        RegistrarMedicaoService().executar(da,ProbeResult(4,3,220))
        RegistrarMedicaoService().executar(dbb,ProbeResult(4,3,330))
        db.session.commit()
        failure=db.session.scalar(select(Falha).where(Falha.dispositivo_id==dbb.id))
        diag=db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id==failure.id))
        metric=db.session.scalar(select(Metrica).where(Metrica.dispositivo_id==dbb.id))
        fid,did,mid=failure.id,diag.id,metric.id
    h=auth_headers(signed)
    for path in [f'/api/dispositivos/{d["id"]}',f'/api/metricas/{mid}',f'/api/falhas/{fid}',f'/api/diagnosticos/{did}',
                 f'/api/metricas?dispositivo_id={d["id"]}',f'/api/falhas?dispositivo_id={d["id"]}',
                 f'/api/dashboard?dispositivo_id={d["id"]}',f'/api/relatorios/exportar?dispositivo_id={d["id"]}']:
        assert signed.get(path).status_code==404,path
    assert signed.put(f'/api/dispositivos/{d["id"]}',json={'nome':'invasao'},headers=h).status_code==404
    assert signed.delete(f'/api/dispositivos/{d["id"]}',headers=h).status_code==404
    assert signed.post(f'/api/dispositivos/{d["id"]}/coletas',json={},headers=h).status_code==404
    assert signed.put(f'/api/falhas/{fid}/impacto',json={'usuarios_afetados':2},headers=h).status_code==404
    assert signed.post('/api/metricas',json={'dispositivo_id':d['id']},headers=h).status_code==405
    assert signed.get('/api/dispositivos').json[0]['nome']=='Roteador'
    assert signed.get('/api/falhas').json['total']==1
    assert signed.get('/api/metricas').json['total']==1
    dash=signed.get('/api/dashboard').json
    assert dash['indicadores']['total']==1 and dash['indicadores']['instaveis']==1
    assert dash['indicadores']['falhas_abertas']==1
    report=signed.get('/api/relatorios/exportar')
    assert report.status_code==200
    with zipfile.ZipFile(io.BytesIO(report.data)) as z:
        assert set(z.namelist())=={'dispositivos.csv','metricas.csv','falhas.csv','diagnosticos.csv','leia-me.json'}
        for f in z.namelist(): assert 'SIGILO-B' not in z.read(f).decode('utf-8-sig')
        assert 'CONGESTIONAMENTO' in z.read('diagnosticos.csv').decode('utf-8-sig')
        assert '220.0' in z.read('metricas.csv').decode('utf-8-sig')
        assert json.loads(z.read('leia-me.json'))['contagens']['falhas']==1

def test_metric_period_order_dashboard_and_csv_injection(app,signed,device):
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        d.nome='=HYPERLINK("malicious")'
        for hours in [4,3,2]: RegistrarMedicaoService().executar(d,ProbeResult(4,4,10+hours),utcnow()-timedelta(hours=hours))
        db.session.commit()
    result=signed.get('/api/metricas?tipo=latencia&limite=2').json
    assert result['total']==3 and len(result['items'])==2
    assert result['items'][0]['coletada_em']<result['items'][1]['coletada_em']
    assert signed.get('/api/metricas?tipo=invalido').status_code==400
    assert signed.get('/api/falhas?severidade=invalida').status_code==400
    assert signed.get('/api/metricas?inicio=2026-10-02&fim=2026-10-01').status_code==400
    assert signed.get('/api/metricas?fim=2020-01-01').status_code==200
    availability=signed.get('/api/metricas?tipo=disponibilidade').json['items'][0]
    assert 'respondeu' in availability and 'latencia_ms' not in availability and 'perda_pacotes_pct' not in availability
    report=signed.get('/api/relatorios/exportar')
    with zipfile.ZipFile(io.BytesIO(report.data)) as z:
        assert "'=HYPERLINK" in z.read('dispositivos.csv').decode('utf-8-sig')
