from datetime import timedelta
from sqlalchemy import select
from app import db
from models import Dispositivo, Falha, Diagnostico, utcnow
from app.services.monitoring import ProbeResult, record_result
from app.services.diagnostics import refresh_company


def rule_codes(failure):
    return {c['regra'] for c in db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id == failure.id)).causas}


def test_localized_and_shared_outage_require_current_peer_evidence(app, device):
    with app.app_context():
        first = db.session.get(Dispositivo, device['id'])
        peer = Dispositivo(empresa_id=first.empresa_id, nome='Outro', ip='127.0.0.2', tipo='Servidor', localizacao='TI')
        db.session.add(peer)
        db.session.flush()
        now = utcnow() - timedelta(seconds=100)
        record_result(peer, ProbeResult(4, 4, 1), now)
        for i in range(3):
            record_result(first, ProbeResult(4, 0, None), now + timedelta(seconds=i + 1))
        failure = db.session.scalar(select(Falha).where(Falha.dispositivo_id == first.id))
        assert rule_codes(failure) == {'LOCALIZADA'}
        for i in range(3):
            record_result(peer, ProbeResult(4, 0, None), now + timedelta(seconds=i + 4))
        assert 'COMPARTILHADA' in rule_codes(failure)
        assert 'LOCALIZADA' not in rule_codes(failure)
        # Stale or future observations must not support a shared-outage claim.
        peer.ultima_coleta = now - timedelta(hours=1)
        refresh_company(first.empresa_id, now + timedelta(seconds=7))
        assert 'COMPARTILHADA' not in rule_codes(failure)


def test_latency_recurrence_and_closed_diagnosis_preserved(app, device):
    with app.app_context():
        d = db.session.get(Dispositivo, device['id'])
        now = utcnow() - timedelta(minutes=10)
        for cycle in range(3):
            at = now + timedelta(minutes=cycle)
            record_result(d, ProbeResult(4, 4, 220), at)
            failure = db.session.scalar(select(Falha).where(Falha.dispositivo_id == d.id, Falha.estado == 'ABERTA'))
            assert 'LATENCIA' in rule_codes(failure)
            if cycle == 2:
                assert 'RECORRENTE' in rule_codes(failure)
            diag = db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id == failure.id))
            evidence = diag.evidencias.copy()
            codes = rule_codes(failure)
            record_result(d, ProbeResult(4, 4, 1), at + timedelta(seconds=10))
            record_result(d, ProbeResult(4, 4, 1), at + timedelta(seconds=20))
            assert failure.estado == 'ENCERRADA'
            assert rule_codes(failure) == codes
            assert diag.evidencias == evidence


def test_severity_duration_and_group_boundaries(app, device):
    with app.app_context():
        d = db.session.get(Dispositivo, device['id'])
        now = utcnow() - timedelta(hours=2)
        record_result(d, ProbeResult(4, 3, 50), now)
        failure = db.session.scalar(select(Falha))
        assert failure.severidade == 'BAIXA'
        for minutes, expected in [(5, 'MEDIA'), (15, 'ALTA'), (60, 'CRITICA')]:
            refresh_company(d.empresa_id, now + timedelta(minutes=minutes))
            assert failure.severidade == expected
        for i in (2, 3):
            other = Dispositivo(empresa_id=d.empresa_id, nome=f'D{i}', ip=f'127.0.0.{i}', tipo='Servidor', localizacao='TI')
            db.session.add(other)
            db.session.flush()
            record_result(other, ProbeResult(4, 3, 50), now + timedelta(seconds=i))
        assert failure.severidade == 'ALTA'
        assert failure.justificativa['dispositivos_afetados'] == 3


def test_shared_outage_survives_peers_recovering_first(app, device):
    # Regression (lab, falha #6): in a group outage the peers' recovery samples are processed
    # before the last device's own sample (batch order by device id). The re-analysis in
    # between must keep COMPARTILHADA, and the group severity must not shrink.
    with app.app_context():
        last = db.session.get(Dispositivo, device['id'])
        peers = []
        for i in (2, 3, 4):
            p = Dispositivo(empresa_id=last.empresa_id, nome=f'Andar {i}', ip=f'127.0.0.{i}', tipo='Switch', localizacao='Andar 2')
            db.session.add(p)
            peers.append(p)
        healthy = Dispositivo(empresa_id=last.empresa_id, nome='Datacenter', ip='127.0.0.9', tipo='Servidor', localizacao='TI')
        db.session.add(healthy)
        db.session.flush()
        now = utcnow() - timedelta(minutes=10)
        group = [*peers, last]
        for cycle in range(3):  # one collector batch per minute, processed in device order
            at = now + timedelta(minutes=cycle)
            record_result(healthy, ProbeResult(4, 4, 1), at)
            for d in group:
                record_result(d, ProbeResult(4, 0, None), at + timedelta(seconds=1))
        failure = db.session.scalar(select(Falha).where(Falha.dispositivo_id == last.id))
        assert 'COMPARTILHADA' in rule_codes(failure) and failure.severidade == 'ALTA'
        # Next batch: the peers answer again (first good sample, still INSTAVEL) before `last`
        # is processed, so at that moment `last` is the only device still OFFLINE.
        at = now + timedelta(minutes=3)
        record_result(healthy, ProbeResult(4, 4, 1), at)
        for p in peers:
            record_result(p, ProbeResult(4, 4, 1), at + timedelta(seconds=1))
        assert {p.status for p in peers} == {'INSTAVEL'} and last.status == 'OFFLINE'
        assert 'COMPARTILHADA' in rule_codes(failure)
        # The peers recover completely (incidents closed) while `last` is still down.
        for p in peers:
            record_result(p, ProbeResult(4, 4, 1), at + timedelta(seconds=30))
        assert all(db.session.scalar(select(Falha).where(Falha.dispositivo_id == p.id)).estado == 'ENCERRADA' for p in peers)
        record_result(last, ProbeResult(4, 0, None), at + timedelta(seconds=31))
        assert 'COMPARTILHADA' in rule_codes(failure)
        assert failure.severidade == 'ALTA' and failure.justificativa['dispositivos_afetados'] == 4
        # Its own recovery then preserves that explanation in the closed incident.
        for s in (40, 50):
            record_result(last, ProbeResult(4, 4, 1), at + timedelta(seconds=s))
        assert failure.estado == 'ENCERRADA' and 'COMPARTILHADA' in rule_codes(failure)


def test_reanalysis_without_recent_samples_keeps_diagnosis(app, device):
    # Regression (lab, falha #11): after a collector outage, the first samples of other devices
    # re-analyse every open incident; a device whose last sample is older than the window must
    # keep its diagnosis instead of turning into EVIDENCIA_INSUFICIENTE.
    with app.app_context():
        d = db.session.get(Dispositivo, device['id'])
        peer = Dispositivo(empresa_id=d.empresa_id, nome='Outro', ip='127.0.0.2', tipo='Servidor', localizacao='TI')
        db.session.add(peer)
        db.session.flush()
        now = utcnow() - timedelta(minutes=30)
        record_result(peer, ProbeResult(4, 4, 1), now)
        for i in range(3):
            record_result(d, ProbeResult(4, 0, None), now + timedelta(seconds=i + 1))
        failure = db.session.scalar(select(Falha).where(Falha.dispositivo_id == d.id))
        diag = db.session.scalar(select(Diagnostico).where(Diagnostico.falha_id == failure.id))
        assert rule_codes(failure) == {'LOCALIZADA'} and diag.estado == 'DISPONIVEL'
        analysed = diag.analisado_em
        # Collector back 10 minutes later: the peer's sample arrives first.
        record_result(peer, ProbeResult(4, 4, 1), now + timedelta(minutes=10))
        assert failure.estado == 'ABERTA'
        assert rule_codes(failure) == {'LOCALIZADA'} and diag.estado == 'DISPONIVEL'
        assert diag.analisado_em == analysed
        # A real new sample of the device is analysed normally again.
        record_result(d, ProbeResult(4, 0, None), now + timedelta(minutes=10, seconds=1))
        assert diag.analisado_em > analysed and rule_codes(failure) == {'LOCALIZADA'}
