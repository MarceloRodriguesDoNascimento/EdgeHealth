from datetime import timedelta
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import os
import pytest
from sqlalchemy import select,func
from app import db
from app.models import Dispositivo,Metrica,Falha,Diagnostico,Impacto,utcnow
from app.services.monitoring import ProbeResult,CollectorError,record_result,real_probe,collect_device,run_cycle
from app.services.diagnostics import refresh_company
from conftest import auth_headers

def test_incident_lifecycle_and_metric_contract(app,device):
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        now=utcnow()-timedelta(minutes=2)
        record_result(d,ProbeResult(4,4,3.2),now)
        assert d.status=='ONLINE'
        assert not db.session.scalar(select(Falha))
        for i in range(3): record_result(d,ProbeResult(4,0,None),now+timedelta(seconds=(i+1)*10))
        assert d.status=='OFFLINE'
        failure=db.session.scalar(select(Falha))
        assert db.session.scalar(select(func.count()).select_from(Falha))==1
        assert failure.tipo=='INDISPONIBILIDADE' and failure.estado=='ABERTA'
        assert failure.severidade=='MEDIA'
        assert db.session.scalar(select(Impacto)).usuarios_afetados is None
        assert db.session.scalar(select(Diagnostico)).estado=='EVIDENCIA_INSUFICIENTE'
        record_result(d,ProbeResult(4,4,2),now+timedelta(seconds=40))
        assert d.status=='INSTAVEL' and failure.estado=='ABERTA'
        record_result(d,ProbeResult(4,4,2),now+timedelta(seconds=50))
        assert d.status=='ONLINE' and failure.estado=='ENCERRADA'
        assert failure.fim>failure.inicio and failure.encerramento=='RECUPERACAO'
        record_result(d,ProbeResult(4,3,250),now+timedelta(seconds=60))
        assert db.session.scalar(select(func.count()).select_from(Falha))==2
        db.session.commit()
        samples=db.session.scalars(select(Metrica).order_by(Metrica.id)).all()
        assert len(samples)==7
        assert samples[1].latencia_ms is None and samples[1].perda_pacotes_pct==100
        assert samples[-1].perda_pacotes_pct==25 and samples[-1].latencia_ms==250
        assert samples[-1].pacotes_enviados==4 and samples[-1].pacotes_recebidos==3

def test_diagnostic_catalog_impact_severity(app,signed,device):
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        record_result(d,ProbeResult(4,3,300))
        db.session.commit()
        f=db.session.scalar(select(Falha))
        id=f.id
        diag=db.session.scalar(select(Diagnostico))
        assert diag.estado=='DISPONIVEL'
        assert 'CONGESTIONAMENTO' in [c['regra'] for c in diag.causas]
        assert diag.evidencias['amostras'][0]['perda_pacotes_pct']==25
    detail=signed.get(f'/api/falhas/{id}').json
    assert detail['diagnostico']['recomendacoes']
    updated=signed.put(f'/api/falhas/{id}/impacto',json={'usuarios_afetados':60,'observacao':'Estimativa da equipe'},headers=auth_headers(signed))
    assert updated.status_code==200
    assert updated.json['severidade']=='CRITICA'
    assert updated.json['impacto']['origem']=='INFORMADO_PELO_USUARIO'
    assert updated.json['justificativa']['usuarios_afetados']==60
    assert signed.put(f'/api/falhas/{id}/impacto',json={'usuarios_afetados':-1},headers=auth_headers(signed)).status_code==400

def test_time_based_severity_and_archive_preserves_history(app,signed,device):
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        record_result(d,ProbeResult(4,3,180),utcnow()-timedelta(minutes=20))
        refresh_company(d.empresa_id)
        db.session.commit()
        f=db.session.scalar(select(Falha))
        assert f.severidade=='ALTA'
        fid=f.id
    assert signed.delete('/api/dispositivos/'+str(device['id']),headers=auth_headers(signed)).status_code==204
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Metrica))==1
        assert db.session.get(Falha,fid).encerramento=='ARQUIVAMENTO'
    assert signed.get('/api/falhas/'+str(fid)).status_code==200

def test_adapter_uses_measurement_and_bounds_errors(monkeypatch):
    from app.services import monitoring
    seen={}
    def fake(address,**kwargs):
        seen.update(address=address,**kwargs)
        return SimpleNamespace(packets_sent=4,packets_received=3,avg_rtt=81.25)
    monkeypatch.setattr(monitoring,'ping',fake)
    result=real_probe('127.0.0.1',4,0.2)
    assert result.loss==25 and result.latency_ms==81.25
    assert seen['privileged'] is False and seen['timeout']==0.2
    with pytest.raises(CollectorError): real_probe('127.0.0.1;echo injection')
    def timeout(*args,**kwargs): raise OSError('Socket timeout')
    monkeypatch.setattr(monitoring,'ping',timeout)
    with pytest.raises(CollectorError): real_probe('127.0.0.1')

def test_scheduler_persists_and_does_not_collect_twice(app,device):
    assert run_cycle(app,lambda *_:ProbeResult(4,4,0.4))==1
    assert run_cycle(app,lambda *_:ProbeResult(4,4,0.4))==0
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        assert d.status=='ONLINE'
        assert db.session.scalar(select(func.count()).select_from(Metrica))==1

def test_collector_error_is_not_a_network_failure(app,device):
    def broken(*_): raise CollectorError('Sem permissão ICMP')
    assert collect_device(app,device['id'],broken) is False
    with app.app_context():
        d=db.session.get(Dispositivo,device['id'])
        assert d.status is None and d.erro_coleta=='Sem permissão ICMP'
        assert db.session.scalar(select(func.count()).select_from(Metrica))==0
        assert db.session.scalar(select(func.count()).select_from(Falha))==0

def test_exclusive_lease(app,device):
    entered,release=Event(),Event()
    def slow(*_):
        entered.set()
        assert release.wait(3)
        return ProbeResult(4,4,1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(collect_device,app,device['id'],slow)
        assert entered.wait(3)
        assert collect_device(app,device['id'],lambda *_:ProbeResult(4,4,1)) is False
        release.set()
        assert first.result()
    with app.app_context(): assert db.session.scalar(select(func.count()).select_from(Metrica))==1

@pytest.mark.real_network
@pytest.mark.skipif(os.getenv('EDGEHEALTH_TEST_REAL_NETWORK')!='1',reason='Habilite teste ICMP de loopback explicitamente.')
def test_real_loopback_adapter():
    result=real_probe('127.0.0.1',2,0.5)
    assert result.sent==2 and result.received==2
    assert result.latency_ms is not None and result.latency_ms>=0
    assert result.loss==0
